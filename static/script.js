/**
 * =============================================
 * 🚀 YouTube ডাউনলোডার - সম্পূর্ণ JavaScript
 * ওয়েবসাইট ক্রিয়েটর: Robbany Bagha
 * =============================================
 */

(function() {
    'use strict';

    // DOM এলিমেন্ট
    const videoUrl = document.getElementById('videoUrl');
    const fetchBtn = document.getElementById('fetchBtn');
    const loader = document.getElementById('loader');
    const loaderProgress = document.getElementById('loaderProgress');
    const videoCard = document.getElementById('videoCard');
    const thumb = document.getElementById('thumb');
    const title = document.getElementById('title');
    const duration = document.getElementById('duration');
    const durationBadge = document.getElementById('durationBadge');
    const views = document.getElementById('views');
    const uploader = document.getElementById('uploader');
    const formatGrid = document.getElementById('formatGrid');
    const downloadBtn = document.getElementById('downloadBtn');
    const toast = document.getElementById('toast');

    let selectedFormat = null;
    let toastTimer = null;

    // টোস্ট
    function showToast(message, type = 'info') {
        toast.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => {
            toast.classList.remove('show');
        }, 4500);
    }

    // ভিডিও আইডি বের করা
    function extractVideoId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)/
        ];
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        const idMatch = url.match(/^[a-zA-Z0-9_-]{11}$/);
        return idMatch ? idMatch[0] : null;
    }

    // ভিডিও তথ্য আনা
    async function fetchVideoInfo(url) {
        const response = await fetch('/api/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'ভিডিও তথ্য পাওয়া যায়নি');
        }

        return await response.json();
    }

    // ডাউনলোড
    async function downloadVideo(url, formatId) {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                url: url, 
                format_id: formatId 
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'ডাউনলোড ব্যর্থ');
        }

        // ফাইল ডাউনলোড
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'video.mp4';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
    }

    // ভিডিও খোঁজা
    async function handleFetch() {
        const url = videoUrl.value.trim();

        if (!url) {
            showToast('⚠️ দয়া করে একটি YouTube লিংক দিন', 'error');
            videoUrl.focus();
            return;
        }

        const videoId = extractVideoId(url);
        if (!videoId) {
            showToast('❌ সঠিক YouTube লিংক দিন', 'error');
            return;
        }

        // লোডার দেখান
        loader.style.display = 'block';
        loaderProgress.style.width = '0%';
        videoCard.style.display = 'none';
        downloadBtn.style.display = 'none';
        fetchBtn.disabled = true;
        fetchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> লোড...';

        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 12;
            if (progress > 90) progress = 90;
            loaderProgress.style.width = progress + '%';
        }, 300);

        try {
            const data = await fetchVideoInfo(url);

            clearInterval(progressInterval);
            loaderProgress.style.width = '100%';

            // ভিডিও তথ্য দেখান
            thumb.src = data.thumbnail || `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
            thumb.alt = data.title;
            title.textContent = data.title.length > 55 ? data.title.slice(0, 55) + '…' : data.title;
            duration.textContent = data.duration || 'N/A';
            durationBadge.textContent = '⏱️ ' + (data.duration || 'N/A');
            views.textContent = data.view_count || '—';
            uploader.textContent = data.uploader || '—';

            // ফরম্যাট বাটন
            formatGrid.innerHTML = '';

            if (data.formats && data.formats.length > 0) {
                data.formats.forEach(format => {
                    const btn = document.createElement('div');
                    btn.className = 'format-btn';
                    btn.innerHTML = `
                        <div class="q">${format.quality}</div>
                        <div class="s">📦 ${format.filesize}</div>
                    `;

                    btn.dataset.formatId = format.format_id;

                    btn.addEventListener('click', () => {
                        document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('selected'));
                        btn.classList.add('selected');
                        selectedFormat = format.format_id;
                        downloadBtn.style.display = 'flex';
                        downloadBtn.innerHTML = `
                            <i class="fas fa-download"></i> ডাউনলোড (${format.quality})
                        `;
                    });

                    formatGrid.appendChild(btn);
                });

                showToast('✅ ভিডিও পাওয়া গেছে!', 'success');
            } else {
                showToast('⚠️ কোনো ডাউনলোড ফরম্যাট নেই', 'error');
            }

            videoCard.style.display = 'block';
            loader.style.display = 'none';

        } catch (error) {
            clearInterval(progressInterval);
            loader.style.display = 'none';
            showToast('❌ ' + (error.message || 'ভিডিও ডাউনলোড করা যাচ্ছে না'), 'error');
        } finally {
            fetchBtn.disabled = false;
            fetchBtn.innerHTML = '<i class="fas fa-search"></i> খুঁজুন';
        }
    }

    // ডাউনলোড হ্যান্ডলার
    downloadBtn.addEventListener('click', async () => {
        if (!selectedFormat) {
            showToast('⚠️ প্রথমে একটি কোয়ালিটি বেছে নিন', 'error');
            return;
        }

        const url = videoUrl.value.trim();
        downloadBtn.disabled = true;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ডাউনলোড হচ্ছে...';

        try {
            await downloadVideo(url, selectedFormat);
            showToast('✅ ডাউনলোড সম্পূর্ণ!', 'success');
        } catch (error) {
            showToast('❌ ' + (error.message || 'ডাউনলোড ব্যর্থ'), 'error');
        } finally {
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<i class="fas fa-download"></i> ডাউনলোড করুন';
        }
    });

    // ইভেন্ট
    fetchBtn.addEventListener('click', handleFetch);
    videoUrl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleFetch();
        }
    });
    videoUrl.addEventListener('paste', () => setTimeout(handleFetch, 500));

    console.log('🎬 YouTube ডাউনলোডার লোড হয়েছে!');
    console.log('👨‍💻 ওয়েবসাইট ক্রিয়েটর: Robbany Bagha');

})();
