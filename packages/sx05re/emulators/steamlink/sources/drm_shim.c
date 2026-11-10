// SPDX-License-Identifier: GPL-2.0
// ioctl shim for Steam Link (drmu, Raspberry Pi build) on the Amlogic vendor DRM driver.
// No hard-coded IDs: planes and properties are resolved at runtime.
//  1. properties the driver refuses to write are learned and filtered out
//  2. video planes (NV12, no RGB) get an IN_FORMATS blob with NV12/NV21/YU12
//  3. YU12 framebuffers are replaced by NV12 shadow buffers, converted before each commit
//  4. uniform buffer size against an H.264 scratch buffer overflow on resolution changes
//  5. all fbdev layers (UI, overlay) are blanked while streaming
#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define DRM_IOCTL_MODE_ATOMIC            0xc03864bcUL
#define DRM_IOCTL_MODE_OBJ_GETPROPERTIES 0xc02064b9UL
#define DRM_IOCTL_MODE_GETPROPERTY       0xc04064aaUL
#define DRM_IOCTL_MODE_GETPROPBLOB       0xc01064acUL
#define DRM_IOCTL_MODE_GETPLANERESOURCES 0xc01064b5UL
#define DRM_IOCTL_MODE_GETPLANE          0xc02064b6UL
#define DRM_IOCTL_MODE_ADDFB2            0xc06864b8UL
#define DRM_IOCTL_MODE_RMFB              0xc00464afUL
#define DRM_IOCTL_PRIME_FD_TO_HANDLE     0xc00c642eUL
#define DMA_HEAP_IOCTL_ALLOC             0xc0184800UL
#define DMA_BUF_IOCTL_SYNC               0x40086200UL

#define FMT_NV12 0x3231564e
#define FMT_NV21 0x3132564e
#define FMT_YU12 0x32315559
#define FMT_AR24 0x34325241
#define FMT_XR24 0x34325258

#define ATOMIC_TEST_ONLY      0x0100
#define ATOMIC_NONBLOCK       0x0200
#define ATOMIC_ALLOW_MODESET  0x0400
#define OBJ_PLANE             0xeeeeeeee
#define FAKE_BLOB             0x7fff0000u
#define MAXP 512
#define ALIGN(x, a) (((x) + (a) - 1) & ~((a) - 1))

struct drm_mode_atomic {
	uint32_t flags, count_objs;
	uint64_t objs_ptr, count_props_ptr, props_ptr, prop_values_ptr, reserved, user_data;
};
struct drm_mode_obj_get_properties {
	uint64_t props_ptr, prop_values_ptr;
	uint32_t count_props, obj_id, obj_type;
};
struct drm_mode_get_property {
	uint64_t values_ptr, enum_blob_ptr;
	uint32_t prop_id, flags;
	char name[32];
	uint32_t count_values, count_enum_blobs;
};
struct drm_mode_get_blob {
	uint32_t blob_id, length;
	uint64_t data;
};
struct drm_mode_get_plane_res {
	uint64_t plane_id_ptr;
	uint32_t count_planes;
};
struct drm_mode_get_plane {
	uint32_t plane_id, crtc_id, fb_id, possible_crtcs, gamma_size, count_format_types;
	uint64_t format_type_ptr;
};
struct drm_mode_fb_cmd2 {
	uint32_t fb_id, width, height, pixel_format, flags;
	uint32_t handles[4], pitches[4], offsets[4];
	uint64_t modifier[4];
};
struct drm_prime_handle {
	uint32_t handle, flags;
	int32_t fd;
};
struct dma_heap_allocation_data {
	uint64_t len;
	uint32_t fd, fd_flags;
	uint64_t heap_flags;
};

static int (*real)(int, unsigned long, ...);
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

/* --- planes and property IDs, resolved once per process --- */
static int inited;
static uint32_t video_planes[8], nvideo;
static uint32_t pid_fb, pid_src_w, pid_src_h, pid_in_formats;
static uint32_t pid_crtc_x, pid_crtc_y, pid_crtc_w, pid_crtc_h;
static uint32_t denied[128], ndenied;

static int prop_name(int fd, uint32_t id, char name[32])
{
	struct drm_mode_get_property p = { .prop_id = id };
	if (real(fd, DRM_IOCTL_MODE_GETPROPERTY, &p))
		return -1;
	memcpy(name, p.name, 32);
	name[31] = 0;
	return 0;
}

static int is_video_plane(uint32_t id)
{
	for (uint32_t i = 0; i < nvideo; i++)
		if (video_planes[i] == id)
			return 1;
	return 0;
}

static void init(int fd)
{
	if (inited)
		return;
	inited = 1;

	uint32_t ids[32];
	struct drm_mode_get_plane_res r = { .plane_id_ptr = (uintptr_t)ids, .count_planes = 32 };
	if (real(fd, DRM_IOCTL_MODE_GETPLANERESOURCES, &r))
		return;
	for (uint32_t i = 0; i < r.count_planes && i < 32; i++) {
		uint32_t fmts[64];
		struct drm_mode_get_plane g = { .plane_id = ids[i], .format_type_ptr = (uintptr_t)fmts, .count_format_types = 64 };
		if (real(fd, DRM_IOCTL_MODE_GETPLANE, &g))
			continue;
		int nv12 = 0, rgb = 0;
		for (uint32_t j = 0; j < g.count_format_types && j < 64; j++) {
			nv12 |= fmts[j] == FMT_NV12;
			rgb |= fmts[j] == FMT_AR24 || fmts[j] == FMT_XR24;
		}
		if (nv12 && !rgb && nvideo < 8)
			video_planes[nvideo++] = ids[i];
	}
	if (!nvideo)
		return;

	/* property IDs are global; resolve names on the first video plane */
	uint32_t pids[64];
	uint64_t vals[64];
	struct drm_mode_obj_get_properties o = { .props_ptr = (uintptr_t)pids, .prop_values_ptr = (uintptr_t)vals,
		.count_props = 64, .obj_id = video_planes[0], .obj_type = OBJ_PLANE };
	if (real(fd, DRM_IOCTL_MODE_OBJ_GETPROPERTIES, &o))
		return;
	for (uint32_t i = 0; i < o.count_props && i < 64; i++) {
		char n[32];
		if (prop_name(fd, pids[i], n))
			continue;
		if (!strcmp(n, "FB_ID"))
			pid_fb = pids[i];
		else if (!strcmp(n, "SRC_W"))
			pid_src_w = pids[i];
		else if (!strcmp(n, "SRC_H"))
			pid_src_h = pids[i];
		else if (!strcmp(n, "IN_FORMATS"))
			pid_in_formats = pids[i];
		else if (!strcmp(n, "CRTC_X"))
			pid_crtc_x = pids[i];
		else if (!strcmp(n, "CRTC_Y"))
			pid_crtc_y = pids[i];
		else if (!strcmp(n, "CRTC_W"))
			pid_crtc_w = pids[i];
		else if (!strcmp(n, "CRTC_H"))
			pid_crtc_h = pids[i];
	}
	fprintf(stderr, "DRMSHIM %u video plane(s), first %u\n", nvideo, video_planes[0]);
}

/* --- 1. learn properties the driver refuses --- */
static int is_denied(uint32_t p)
{
	for (uint32_t i = 0; i < ndenied; i++)
		if (denied[i] == p)
			return 1;
	return 0;
}

static int core_prop(const char *n)
{
	static const char *core[] = { "CRTC_ID", "FB_ID", "SRC_X", "SRC_Y", "SRC_W", "SRC_H",
		"CRTC_X", "CRTC_Y", "CRTC_W", "CRTC_H", "ACTIVE", "MODE_ID" };
	for (unsigned i = 0; i < sizeof(core) / sizeof(*core); i++)
		if (!strcmp(n, core[i]))
			return 1;
	return 0;
}

/* test each property alone; whatever fails on its own is blocked */
static int learn(int fd, const uint32_t *o, const uint32_t *c, const uint32_t *p, const uint64_t *v, uint32_t no)
{
	int added = 0;
	for (uint32_t i = 0, k = 0; i < no; i++)
		for (uint32_t j = 0; j < c[i]; j++, k++) {
			char n[32];
			if (is_denied(p[k]) || prop_name(fd, p[k], n) || core_prop(n))
				continue;
			uint32_t one = 1;
			struct drm_mode_atomic t = { .flags = ATOMIC_TEST_ONLY | ATOMIC_ALLOW_MODESET, .count_objs = 1,
				.objs_ptr = (uintptr_t)&o[i], .count_props_ptr = (uintptr_t)&one,
				.props_ptr = (uintptr_t)&p[k], .prop_values_ptr = (uintptr_t)&v[k] };
			if (real(fd, DRM_IOCTL_MODE_ATOMIC, &t) && errno == EINVAL && ndenied < 128) {
				denied[ndenied++] = p[k];
				added = 1;
				fprintf(stderr, "DRMSHIM property '%s' (%u) blocked\n", n, p[k]);
			}
		}
	return added;
}

/* --- 2. IN_FORMATS blob for the video planes --- */
static const struct {
	uint32_t version, flags, count_formats, formats_offset, count_modifiers, modifiers_offset;
	uint32_t formats[4]; /* 3 used, 1 padding to 8 bytes */
	uint64_t mod_formats;
	uint32_t mod_offset, mod_pad;
	uint64_t modifier;
} fake_in_formats = { 1, 0, 3, 24, 1, 40, { FMT_NV12, FMT_NV21, FMT_YU12, 0 }, 7, 0, 0, 0 };

/* --- 3. YU12 -> NV12 --- */
#define MAXH 256
#define MAXFB 64
static struct { uint32_t handle; int fd; } hmap[MAXH];
static struct conv {
	uint32_t fb_id, w, h, pitch[3], offset[3];
	uint32_t dst_handle, disp_fb, disp_w, disp_h; /* display FB for the current picture size */
	uint8_t *src, *dst;
	size_t src_len, dst_len;
	int src_fd, dst_fd;
} conv[MAXFB];
static int nconv, nh;
static volatile int vid_w, vid_h; /* actual picture size of the stream */

static int handle_fd(uint32_t h)
{
	for (int i = 0; i < nh; i++)
		if (hmap[i].handle == h)
			return hmap[i].fd;
	return -1;
}

static void buf_sync(int fd, uint64_t flags)
{
	real(fd, DMA_BUF_IOCTL_SYNC, &flags);
}

static int addfb_yu12(int fd, struct drm_mode_fb_cmd2 *c)
{
	int sfd = handle_fd(c->handles[0]);
	if (sfd < 0 || nconv >= MAXFB)
		return -1;
	struct conv *v = &conv[nconv];
	v->w = c->width;
	v->h = c->height;
	for (int i = 0; i < 3; i++) {
		v->pitch[i] = c->pitches[i];
		v->offset[i] = c->offsets[i];
	}
	v->src_len = c->offsets[2] + (size_t)c->pitches[2] * ((c->height + 1) / 2);
	v->src = mmap(NULL, v->src_len, PROT_READ, MAP_SHARED, sfd, 0);
	if (v->src == MAP_FAILED)
		return -1;
	v->src_fd = sfd;

	/* contiguous memory for the video plane */
	v->dst_len = (size_t)ALIGN(c->width, 64) * ALIGN(c->height, 32) * 3 / 2;
	int heap = open("/dev/dma_heap/heap-codecmm", O_RDWR | O_CLOEXEC);
	struct dma_heap_allocation_data a = { .len = v->dst_len, .fd_flags = O_RDWR | O_CLOEXEC };
	if (heap < 0 || real(heap, DMA_HEAP_IOCTL_ALLOC, &a)) {
		if (heap >= 0)
			close(heap);
		munmap(v->src, v->src_len);
		return -1;
	}
	close(heap);
	v->dst_fd = a.fd;
	v->dst = mmap(NULL, v->dst_len, PROT_READ | PROT_WRITE, MAP_SHARED, v->dst_fd, 0);
	struct drm_prime_handle ph = { .fd = v->dst_fd };
	if (v->dst == MAP_FAILED || real(fd, DRM_IOCTL_PRIME_FD_TO_HANDLE, &ph))
		return -1;

	struct drm_mode_fb_cmd2 n = { .width = c->width, .height = c->height, .pixel_format = FMT_NV12 };
	n.handles[0] = n.handles[1] = ph.handle;
	n.pitches[0] = n.pitches[1] = ALIGN(c->width, 64);
	n.offsets[1] = ALIGN(c->width, 64) * ALIGN(c->height, 32);
	if (real(fd, DRM_IOCTL_MODE_ADDFB2, &n))
		return -1;
	c->fb_id = v->fb_id = n.fb_id;
	v->dst_handle = ph.handle;
	v->disp_fb = v->disp_w = v->disp_h = 0;
	nconv++;
	return 0;
}

/* The vendor driver assumes pitch == width and UV right after SRC_H lines, and rounds
 * width/height up: FB with aligned size, black border, SRC = whole FB */
static uint32_t disp_fb(int fd, struct conv *v, uint32_t w, uint32_t h)
{
	if (v->disp_fb && v->disp_w == w && v->disp_h == h)
		return v->disp_fb;
	if (v->disp_fb)
		real(fd, DRM_IOCTL_MODE_RMFB, &v->disp_fb);
	uint32_t fw = ALIGN(w, 64), fh = ALIGN(h, 32);
	memset(v->dst, 16, (size_t)fw * fh);
	memset(v->dst + (size_t)fw * fh, 128, (size_t)fw * fh / 2);
	struct drm_mode_fb_cmd2 n = { .width = fw, .height = fh, .pixel_format = FMT_NV12 };
	n.handles[0] = n.handles[1] = v->dst_handle;
	n.pitches[0] = n.pitches[1] = fw;
	n.offsets[1] = fw * fh;
	if (real(fd, DRM_IOCTL_MODE_ADDFB2, &n)) {
		v->disp_fb = 0;
		return v->fb_id;
	}
	v->disp_fb = n.fb_id;
	v->disp_w = w;
	v->disp_h = h;
	return v->disp_fb;
}

/* convert and return the FB ID to scan out */
static uint64_t convert(int fd, uint32_t fb_id)
{
	for (int i = 0; i < nconv; i++) {
		struct conv *v = &conv[i];
		if (v->fb_id != fb_id)
			continue;
		uint32_t w = (vid_w && (uint32_t)vid_w < v->w ? (uint32_t)vid_w : v->w) & ~1u;
		uint32_t h = (vid_h && (uint32_t)vid_h < v->h ? (uint32_t)vid_h : v->h) & ~1u;
		uint32_t fb = disp_fb(fd, v, w, h);
		uint32_t fw = ALIGN(w, 64), fh = ALIGN(h, 32);
		buf_sync(v->src_fd, 0 | 1);   /* START | READ */
		/* no sync on dst: it would wait for the video plane fence, which is never signalled */
		for (uint32_t y = 0; y < h; y++)
			memcpy(v->dst + (size_t)y * fw, v->src + v->offset[0] + (size_t)y * v->pitch[0], w);
		uint8_t *uv = v->dst + (size_t)fw * fh;
		for (uint32_t y = 0; y < h / 2; y++) {
			const uint8_t *u = v->src + v->offset[1] + (size_t)y * v->pitch[1];
			const uint8_t *q = v->src + v->offset[2] + (size_t)y * v->pitch[2];
			uint8_t *d = uv + (size_t)y * fw;
			for (uint32_t x = 0; x < w / 2; x++) {
				d[2 * x] = u[x];
				d[2 * x + 1] = q[x];
			}
		}
		buf_sync(v->src_fd, 4 | 1);   /* END | READ */
		return fb;
	}
	return fb_id;
}

/* --- 4. uniform buffer size: drmu reuses buffers of other sizes, but FFmpeg's
 *        H.264 scratch buffers are sized for the first pitch --- */
void avcodec_align_dimensions2(void *s, int *w, int *h, int linesize_align[8])
{
	static void (*real_align)(void *, int *, int *, int *);
	if (!real_align)
		real_align = dlsym(RTLD_NEXT, "avcodec_align_dimensions2");
	/* remember the real size: AVCodecContext.width/height (FFmpeg 5.1: offset 116/120) */
	int cw = *(int *)((char *)s + 116), ch = *(int *)((char *)s + 120);
	if (cw > 0 && cw <= 4096 && ch > 0 && ch <= 4096 && (cw != vid_w || ch != vid_h)) {
		vid_w = cw;
		vid_h = ch;
		fprintf(stderr, "DRMSHIM video size %dx%d\n", cw, ch);
	}
	real_align(s, w, h, linesize_align);
	if (*w < 1920)
		*w = 1920;
	if (*h < 1088)
		*h = 1088;
}

/* --- 5. fbdev layers sit above the video and are blended incorrectly --- */
static void osd_blank(int on)
{
	static int state = -1;
	if (state == on)
		return;
	state = on;
	DIR *d = opendir("/sys/class/graphics");
	struct dirent *e;
	while (d && (e = readdir(d))) {
		if (strncmp(e->d_name, "fb", 2))
			continue;
		char path[300];
		snprintf(path, sizeof(path), "/sys/class/graphics/%s/blank", e->d_name);
		int b = open(path, O_WRONLY | O_CLOEXEC);
		if (b >= 0) {
			if (write(b, on ? "1" : "0", 1) < 0)
				perror("DRMSHIM blank");
			close(b);
		}
	}
	if (d)
		closedir(d);
}

static int atomic(int fd, struct drm_mode_atomic *a)
{
	const uint32_t *objs = (void *)(uintptr_t)a->objs_ptr, *cnt = (void *)(uintptr_t)a->count_props_ptr;
	const uint32_t *props = (void *)(uintptr_t)a->props_ptr;
	const uint64_t *vals = (void *)(uintptr_t)a->prop_values_ptr;
	uint32_t o[MAXP], c[MAXP], p[MAXP], no = 0, np = 0, k = 0;
	uint64_t v[MAXP];
	int video = 0;

	for (uint32_t i = 0; i < a->count_objs && no < MAXP; i++) {
		uint32_t n = 0;
		int cx = -1, cy = -1, cw = -1, ch = -1; /* positions of CRTC_X/Y/W/H in v[] */
		for (uint32_t j = 0; j < cnt[i]; j++, k++) {
			if (is_denied(props[k]) || np >= MAXP)
				continue;
			p[np] = props[k];
			v[np] = vals[k];
			if (is_video_plane(objs[i])) {
				if (props[k] == pid_crtc_x)
					cx = np;
				else if (props[k] == pid_crtc_y)
					cy = np;
				else if (props[k] == pid_crtc_w)
					cw = np;
				else if (props[k] == pid_crtc_h)
					ch = np;
				if (props[k] == pid_fb) {
					if (!(a->flags & ATOMIC_TEST_ONLY))
						osd_blank(vals[k] != 0);
					if (vals[k]) {
						video = 1;
						pthread_mutex_lock(&lock);
						v[np] = convert(fd, vals[k]);
						pthread_mutex_unlock(&lock);
					}
				} else if (vid_w && props[k] == pid_src_w) {
					v[np] = (uint64_t)ALIGN((uint32_t)vid_w & ~1u, 64) << 16;
				} else if (vid_h && props[k] == pid_src_h) {
					v[np] = (uint64_t)ALIGN((uint32_t)vid_h & ~1u, 32) << 16;
				}
			}
			np++;
			n++;
		}
		/* target rect from the real picture size: drmu uses the raised buffer size
		 * (1920x1088) and would stretch narrow pictures to full width */
		if (vid_w && vid_h && cx >= 0 && cy >= 0 && cw >= 0 && ch >= 0) {
			int64_t sw = 2 * (int64_t)(int32_t)v[cx] + (int64_t)v[cw];
			int64_t sh = 2 * (int64_t)(int32_t)v[cy] + (int64_t)v[ch];
			/* source is the whole aligned FB: use its size */
			int64_t fw = ALIGN((uint32_t)vid_w & ~1u, 64), fh = ALIGN((uint32_t)vid_h & ~1u, 32);
			int64_t w = sh * fw / fh, h = sh;
			if (w > sw) {
				w = sw;
				h = sw * fh / fw;
			}
			v[cx] = (uint64_t)(uint32_t)(int32_t)((sw - w) / 2);
			v[cy] = (uint64_t)(uint32_t)(int32_t)((sh - h) / 2);
			v[cw] = (uint64_t)w;
			v[ch] = (uint64_t)h;
		}
		if (n) {
			o[no] = objs[i];
			c[no++] = n;
		}
	}
	if (!no)
		return 0; /* only blocked properties: treat as success */

	struct drm_mode_atomic b = *a;
	/* never block video commits: the vendor driver does not signal the fence */
	if (video && !(b.flags & ATOMIC_TEST_ONLY))
		b.flags |= ATOMIC_NONBLOCK;
	b.count_objs = no;
	b.objs_ptr = (uintptr_t)o;
	b.count_props_ptr = (uintptr_t)c;
	b.props_ptr = (uintptr_t)p;
	b.prop_values_ptr = (uintptr_t)v;
	int r = real(fd, DRM_IOCTL_MODE_ATOMIC, &b);
	if (r && errno == EINVAL) {
		pthread_mutex_lock(&lock);
		int added = learn(fd, o, c, p, v, no);
		pthread_mutex_unlock(&lock);
		if (added)
			return atomic(fd, a);
		errno = EINVAL;
	}
	return r;
}

int ioctl(int fd, unsigned long req, ...)
{
	if (!real)
		real = dlsym(RTLD_NEXT, "ioctl");
	va_list ap;
	va_start(ap, req);
	void *arg = va_arg(ap, void *);
	va_end(ap);

	if (req == DRM_IOCTL_PRIME_FD_TO_HANDLE) {
		struct drm_prime_handle *p = arg;
		int r = real(fd, req, arg);
		pthread_mutex_lock(&lock);
		if (!r) { /* the kernel reuses handles: replace the entry */
			int i = 0;
			while (i < nh && hmap[i].handle != p->handle)
				i++;
			if (i < nh)
				close(hmap[i].fd);
			if (i < MAXH) {
				hmap[i].handle = p->handle;
				hmap[i].fd = dup(p->fd);
				if (i == nh)
					nh++;
			}
		}
		pthread_mutex_unlock(&lock);
		return r;
	}

	if (req == DRM_IOCTL_MODE_ADDFB2 && ((struct drm_mode_fb_cmd2 *)arg)->pixel_format == FMT_YU12) {
		pthread_mutex_lock(&lock);
		int r = addfb_yu12(fd, arg);
		pthread_mutex_unlock(&lock);
		if (!r)
			return 0;
		fprintf(stderr, "DRMSHIM YU12 conversion failed\n");
		return real(fd, req, arg);
	}

	if (req == DRM_IOCTL_MODE_OBJ_GETPROPERTIES) {
		pthread_mutex_lock(&lock);
		init(fd);
		pthread_mutex_unlock(&lock);
		struct drm_mode_obj_get_properties *g = arg;
		if (!pid_in_formats || !is_video_plane(g->obj_id))
			return real(fd, req, arg);
		struct drm_mode_obj_get_properties t = *g;
		uint32_t ids[64];
		uint64_t vals[64];
		t.count_props = 63;
		t.props_ptr = (uintptr_t)ids;
		t.prop_values_ptr = (uintptr_t)vals;
		int r = real(fd, req, &t);
		if (r)
			return r;
		uint32_t n = t.count_props < 63 ? t.count_props : 63, i = 0;
		while (i < n && ids[i] != pid_in_formats)
			i++;
		ids[i] = pid_in_formats; /* replace an existing IN_FORMATS, else append */
		vals[i] = FAKE_BLOB;
		if (i == n)
			n++;
		if (g->props_ptr && g->count_props >= n) {
			memcpy((void *)(uintptr_t)g->props_ptr, ids, n * sizeof(*ids));
			memcpy((void *)(uintptr_t)g->prop_values_ptr, vals, n * sizeof(*vals));
		}
		g->count_props = n;
		return 0;
	}

	if (req == DRM_IOCTL_MODE_GETPROPBLOB && ((struct drm_mode_get_blob *)arg)->blob_id == FAKE_BLOB) {
		struct drm_mode_get_blob *b = arg;
		if (b->data && b->length >= sizeof(fake_in_formats))
			memcpy((void *)(uintptr_t)b->data, &fake_in_formats, sizeof(fake_in_formats));
		b->length = sizeof(fake_in_formats);
		return 0;
	}

	if (req == DRM_IOCTL_MODE_ATOMIC) {
		pthread_mutex_lock(&lock);
		init(fd);
		pthread_mutex_unlock(&lock);
		return atomic(fd, arg);
	}

	return real(fd, req, arg);
}
