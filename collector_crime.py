<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>An Ninh 24H &bull; Tin Nhanh Pháp Luật & Trật Tự Xã Hội</title>

  <!-- PWA Manifest & Theme -->
  <link rel="manifest" href="./manifest.json">
  <meta name="theme-color" content="#881337">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

  <!-- Tailwind CSS & Supabase JS v2 -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>

  <!-- Google Fonts: Inter & JetBrains Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">

  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'sans-serif'],
            mono: ['JetBrains Mono', 'monospace']
          },
          colors: {
            law: {
              red: '#991b1b',
              darkRed: '#7f1d1d',
              lightRed: '#fef2f2',
              gold: '#f59e0b'
            }
          }
        }
      }
    }
  </script>

  <style>
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
    .article-modal-body h2 { font-size: 1.15rem; font-weight: 800; margin-top: 1.25rem; margin-bottom: 0.5rem; color: #1e293b; }
    .article-modal-body p { margin-bottom: 0.85rem; line-height: 1.75; color: #334155; font-size: 0.95rem; text-align: justify; }
    .article-modal-body img { border-radius: 0.75rem; margin: 1rem 0; width: 100%; object-fit: cover; }
    .article-modal-body figcaption { font-size: 0.8rem; color: #64748b; font-style: italic; text-align: center; margin-top: -0.5rem; margin-bottom: 1rem; }
  </style>
</head>
<body class="bg-[#f8fafc] text-slate-800 min-h-screen flex flex-col font-sans antialiased">

  <!-- ================= TOP HEADER ================= -->
  <header class="bg-law-darkRed text-white sticky top-0 z-40 shadow-md">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3 cursor-pointer select-none shrink-0" onclick="filterNews('ALL')">
        <div class="w-10 h-10 rounded-2xl bg-amber-400 text-law-darkRed flex items-center justify-center font-black text-2xl shadow-sm">⚖</div>
        <div>
          <div class="font-black text-xl tracking-tight leading-none text-white">AN NINH <span class="text-amber-400">24H</span></div>
          <span class="text-[9px] text-red-200 font-mono tracking-widest uppercase">Pháp Đình & Trật Tự Xã Hội</span>
        </div>
      </div>

      <div class="flex-grow max-w-xl relative text-slate-800 hidden sm:block">
        <input 
          type="text" 
          id="search-input"
          placeholder="Tìm kiếm vụ án, thủ đoạn lừa đảo, địa bàn..." 
          class="w-full bg-white/95 rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none shadow-inner placeholder:text-slate-400"
          oninput="handleSearch()"
        />
        <svg class="w-4 h-4 text-slate-400 absolute left-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
        </svg>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-950/80 border border-red-800 text-[11px] font-mono text-amber-300">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Trực tuyến</span>
        </span>
      </div>
    </div>

    <!-- Navigation Menu -->
    <nav class="bg-red-950 border-t border-red-900/60 text-xs">
      <div class="max-w-7xl mx-auto px-4 flex items-center gap-1 overflow-x-auto no-scrollbar py-1.5 font-medium" id="category-nav">
        <button onclick="filterNews('ALL')" class="cat-btn px-3 py-1.5 rounded-lg bg-red-800 text-white font-bold shrink-0 transition" data-cat="ALL">Tất cả tin</button>
        <button onclick="filterNews('trong_an')" class="cat-btn px-3 py-1.5 rounded-lg hover:bg-red-900 text-red-200 shrink-0 transition" data-cat="trong_an">🔥 Trọng án</button>
        <button onclick="filterNews('lua_dao')" class="cat-btn px-3 py-1.5 rounded-lg hover:bg-red-900 text-red-200 shrink-0 transition" data-cat="lua_dao">⚠️ Cảnh báo lừa đảo</button>
        <button onclick="filterNews('phap_dinh')" class="cat-btn px-3 py-1.5 rounded-lg hover:bg-red-900 text-red-200 shrink-0 transition" data-cat="phap_dinh">⚖ Pháp đình & Xét xử</button>
        <button onclick="filterNews('an_ninh_dia_phuong')" class="cat-btn px-3 py-1.5 rounded-lg hover:bg-red-900 text-red-200 shrink-0 transition" data-cat="an_ninh_dia_phuong">🛡 An ninh cơ sở</button>
      </div>
    </nav>
  </header>

  <!-- ================= TICKER TIN NÓNG KHẨN CẤP ================= -->
  <section class="bg-amber-100 border-b border-amber-200 text-amber-950 text-xs py-2 px-4 shadow-inner">
    <div class="max-w-7xl mx-auto flex items-center gap-2">
      <span class="font-black bg-law-red text-white px-2 py-0.5 rounded text-[10px] uppercase font-mono tracking-wider shrink-0">TIN NÓNG</span>
      <div id="breaking-ticker" class="truncate font-semibold text-law-darkRed">
        Đang tải thông báo khẩn cấp từ các cơ quan chức năng...
      </div>
    </div>
  </section>

  <!-- ================= NỘI DUNG CHÍNH ================= -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-grow w-full space-y-6">

    <!-- Trạng thái tải tin -->
    <div id="loading-state" class="py-20 text-center space-y-3">
      <div class="w-9 h-9 border-4 border-law-red border-t-transparent rounded-full animate-spin mx-auto"></div>
      <p class="text-xs font-mono text-slate-500">Đang kết nối cơ sở dữ liệu Supabase và đồng bộ tin tức...</p>
    </div>

    <!-- Thông báo rỗng -->
    <div id="empty-state" class="hidden py-16 text-center bg-white rounded-3xl border border-slate-200 p-8 space-y-3">
      <span class="text-4xl">📂</span>
      <h3 class="font-bold text-base text-slate-800">Không tìm thấy tin bài nào</h3>
      <p class="text-xs text-slate-500 font-mono">Hãy thử kiểm tra lại từ khóa hoặc đảm bảo bot `collector_crime.py` đã đồng bộ tin vào bảng `crime_news`.</p>
    </div>

    <!-- Lưới hiển thị tin tức -->
    <section id="news-section" class="hidden space-y-4">
      <div class="flex items-center justify-between border-b border-slate-200 pb-2.5">
        <h2 id="section-title" class="font-bold text-sm sm:text-base text-slate-900 uppercase font-mono flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-law-red"></span>
          Danh Sách Tin Tức Mới Nhất
        </h2>
        <span id="news-count" class="px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-700 text-xs font-mono font-semibold">0 tin</span>
      </div>

      <div id="news-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5"></div>
    </section>

  </main>

  <!-- ================= MODAL XEM CHI TIẾT BÀI BÁO ================= -->
  <div id="article-modal" class="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5 hidden">
    <div class="bg-white rounded-3xl max-w-3xl w-full p-6 sm:p-8 shadow-2xl border border-slate-200 max-h-[92vh] flex flex-col relative animate-in fade-in zoom-in duration-200">
      
      <!-- Nút đóng -->
      <button onclick="closeArticleModal()" class="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center font-bold text-sm transition">
        ✕
      </button>

      <!-- Header bài viết -->
      <div class="border-b border-slate-100 pb-3 mb-4 pr-8 shrink-0">
        <div class="flex items-center gap-2 text-[11px] font-mono text-slate-400 mb-1.5">
          <span id="modal-category" class="px-2 py-0.5 rounded font-bold uppercase bg-red-50 text-law-red"></span>
          <span>&bull;</span>
          <span id="modal-location" class="text-slate-600 font-semibold"></span>
          <span>&bull;</span>
          <span id="modal-source" class="text-slate-500 font-bold"></span>
        </div>
        <h1 id="modal-title" class="text-base sm:text-lg font-bold text-slate-900 leading-snug"></h1>
      </div>

      <!-- Nội dung bài viết cuộn được -->
      <div class="overflow-y-auto pr-1 text-slate-700 text-sm leading-relaxed custom-scroll" id="modal-body-container">
        <p id="modal-summary" class="font-semibold text-slate-900 bg-slate-50 p-3.5 rounded-xl border border-slate-200/80 mb-4 text-xs sm:text-sm"></p>
        <div id="modal-content" class="article-modal-body"></div>
      </div>

      <!-- Footer modal -->
      <div class="border-t border-slate-100 pt-3 mt-4 flex items-center justify-between text-xs font-mono text-slate-400 shrink-0">
        <a id="modal-source-link" href="#" target="_blank" class="text-law-red hover:underline font-bold">
          Xem bài gốc trên trang báo &rarr;
        </a>
        <button onclick="closeArticleModal()" class="px-4 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold">
          Đóng
        </button>
      </div>

    </div>
  </div>

  <footer class="bg-slate-900 text-slate-400 text-center py-6 text-xs border-t border-slate-800 font-mono mt-auto">
    An Ninh 24H &bull; Nền Tảng Cập Nhật & Tổng Hợp Tin Tức Pháp Luật, Tội Phạm Chính Thống
  </footer>

  <!-- ================= KỊCH BẢN KẾT NỐI SUPABASE ================= -->
  <script>
    const SUPABASE_URL = "https://lleeibzegmnycuingzgx.supabase.co";
    const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE";
    const client = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

    let allNews = [];
    let currentCategory = 'ALL';

    const categoryNames = {
      'trong_an': 'Trọng án',
      'lua_dao': 'Cảnh báo lừa đảo',
      'phap_dinh': 'Pháp đình',
      'an_ninh_dia_phuong': 'An ninh cơ sở'
    };

    async function fetchCrimeNews() {
      try {
        const { data, error } = await client
          .from('crime_news')
          .select('*')
          .order('id', { ascending: false });

        document.getElementById('loading-state').classList.add('hidden');

        if (error) {
          console.error("Lỗi truy vấn Supabase:", error);
          document.getElementById('empty-state').classList.remove('hidden');
          return;
        }

        if (data && data.length > 0) {
          allNews = data;
          document.getElementById('news-section').classList.remove('hidden');
          setupBreakingNews(allNews);
          renderNews(allNews);
        } else {
          document.getElementById('empty-state').classList.remove('hidden');
        }
      } catch (err) {
        console.error("Lỗi ngoại lệ:", err);
        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('empty-state').classList.remove('hidden');
      }
    }

    function setupBreakingNews(list) {
      const breaking = list.find(item => item.is_breaking) || list[0];
      if (breaking) {
        document.getElementById('breaking-ticker').innerText = `[${breaking.location}] ${breaking.title}`;
        document.getElementById('breaking-ticker').onclick = () => openArticle(breaking.id);
        document.getElementById('breaking-ticker').classList.add('cursor-pointer', 'hover:underline');
      }
    }

    function renderNews(list) {
      const grid = document.getElementById('news-grid');
      document.getElementById('news-count').innerText = `${list.length} tin bài`;

      if (list.length === 0) {
        grid.innerHTML = `<div class="col-span-full py-12 text-center text-slate-400 font-mono text-xs">Không có bài viết nào khớp với tiêu chí tìm kiếm.</div>`;
        return;
      }

      grid.innerHTML = list.map(item => {
        const catLabel = categoryNames[item.category] || item.category;
        return `
          <article onclick="openArticle(${item.id})" class="bg-white rounded-2xl border border-slate-200/90 overflow-hidden shadow-xs hover:shadow-md transition flex flex-col justify-between group cursor-pointer">
            <div>
              <div class="aspect-[16/10] bg-slate-100 overflow-hidden relative border-b border-slate-100">
                <img src="${item.cover_image}" alt="${item.title}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                <span class="absolute top-2.5 left-2.5 px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-law-darkRed text-white uppercase shadow-xs">
                  ${catLabel}
                </span>
                <span class="absolute bottom-2 left-2 px-2 py-0.5 rounded text-[10px] font-semibold bg-black/75 text-white backdrop-blur-xs">
                  📍 ${item.location}
                </span>
                ${item.is_breaking ? '<span class="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[9px] font-black bg-amber-400 text-slate-900 uppercase">Khẩn</span>' : ''}
              </div>

              <div class="p-4">
                <div class="text-[10px] font-mono text-slate-400 uppercase font-semibold mb-1">${item.source_name}</div>
                <h3 class="font-bold text-xs sm:text-sm text-slate-900 leading-snug line-clamp-2 group-hover:text-law-red transition mb-2">
                  ${item.title}
                </h3>
                <p class="text-xs text-slate-600 line-clamp-3 leading-relaxed">
                  ${item.summary}
                </p>
              </div>
            </div>

            <div class="p-4 pt-0 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-400 mt-2 pt-2.5">
              <span>Đọc toàn văn &rarr;</span>
            </div>
          </article>
        `;
      }).join('');
    }

    function filterNews(cat) {
      currentCategory = cat;
      document.querySelectorAll('.cat-btn').forEach(btn => {
        if (btn.getAttribute('data-cat') === cat) {
          btn.className = "cat-btn px-3 py-1.5 rounded-lg bg-red-800 text-white font-bold shrink-0 transition";
        } else {
          btn.className = "cat-btn px-3 py-1.5 rounded-lg hover:bg-red-900 text-red-200 shrink-0 transition";
        }
      });

      const filtered = (cat === 'ALL') ? allNews : allNews.filter(n => n.category === cat);
      renderNews(filtered);
    }

    function handleSearch() {
      const q = document.getElementById('search-input').value.toLowerCase().trim();
      const filtered = allNews.filter(item => {
        const matchCat = (currentCategory === 'ALL') || (item.category === currentCategory);
        const matchText = (!q) || item.title.toLowerCase().includes(q) || item.location.toLowerCase().includes(q) || item.summary.toLowerCase().includes(q);
        return matchCat && matchText;
      });
      renderNews(filtered);
    }

    function openArticle(id) {
      const item = allNews.find(n => n.id === id);
      if (!item) return;

      document.getElementById('modal-title').innerText = item.title;
      document.getElementById('modal-category').innerText = categoryNames[item.category] || item.category;
      document.getElementById('modal-location').innerText = `Địa bàn: ${item.location}`;
      document.getElementById('modal-source').innerText = `Nguồn: ${item.source_name}`;
      document.getElementById('modal-summary').innerText = item.summary;
      document.getElementById('modal-content').innerHTML = item.content_html;
      document.getElementById('modal-source-link').href = item.source_url || '#';

      document.getElementById('article-modal').classList.remove('hidden');
    }

    function closeArticleModal() {
      document.getElementById('article-modal').classList.add('hidden');
    }

    // PWA Service Worker Registration
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
          .then(reg => console.log('PWA Service Worker ready:', reg.scope))
          .catch(err => console.error('PWA Error:', err));
      });
    }

    window.addEventListener('DOMContentLoaded', fetchCrimeNews);
  </script>
</body>
</html>
