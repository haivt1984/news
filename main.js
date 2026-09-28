// Cấu hình kết nối Supabase
const SUPABASE_URL = "https://lleeibzegmnycuingzgx.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxsZWVpYnplZ21ueWN1aW5nemd4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAxMjc5OTUsImV4cCI6MjEwNTcwMzk5NX0.KrO8Y8qoKh0NIPYDL6wki7zGb-Lxi1xwWgQrX9xSXxE";
const client = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

let allNews = [];
let currentCategory = 'ALL';
let currentLocation = 'ALL';

const categoryNames = {
  'trong_an': 'Trọng án',
  'lua_dao': 'Cảnh báo lừa đảo',
  'phap_dinh': 'Pháp đình & Xét xử',
  'giao_thong': 'Giao thông & Đô thị',
  'an_ninh_dia_phuong': 'An ninh trật tự'
};

// Hàm đảm bảo ảnh load qua Proxy chống chặn 403 trên thiết bị di động
function getSafeImageUrl(url) {
  if (!url || typeof url !== 'string') return '';
  if (url.includes('images.weserv.nl')) return url;
  const clean = url.replace(/^https?:\/\//i, '');
  return `https://images.weserv.nl/?url=${encodeURIComponent(clean)}&w=800&fit=cover&output=webp`;
}

function handleImgError(el) {
  el.onerror = null;
  el.src = "data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22800%22%20height%3D%22500%22%20viewBox%3D%220%200%20800%20500%22%3E%3Crect%20fill%3D%22%23f1f5f9%22%20width%3D%22800%22%20height%3D%22500%22%2F%3E%3Ctext%20fill%3D%22%2394a3b8%22%20font-family%3D%22sans-serif%22%20font-size%3D%2224%22%20dy%3D%2210.5%22%20font-weight%3D%22bold%22%20x%3D%2250%25%22%20y%3D%2250%25%22%20text-anchor%3D%22middle%22%3EH%C3%ACnh%20%E1%BA%A3nh%20t%C6%B0%20li%E1%BB%87u%20v%E1%BB%A5%20%C3%A1n%3C%2Ftext%3E%3C%2Fsvg%3E";
}

// Đồng hồ thời gian thực
function updateClock() {
  const now = new Date();
  const str = now.toLocaleDateString('vi-VN', { weekday: 'short', month: 'numeric', day: 'numeric' }) + " | " + now.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  const clockEl = document.getElementById('live-clock');
  if (clockEl) clockEl.innerText = str;
}
setInterval(updateClock, 1000);
updateClock();

// Lấy danh sách tin từ Supabase
async function fetchCrimeNews() {
  try {
    const loadingEl = document.getElementById('loading-state');
    if (loadingEl) loadingEl.classList.remove('hidden');

    const { data, error } = await client
      .from('crime_news')
      .select('*')
      .order('id', { ascending: false });

    if (loadingEl) loadingEl.classList.add('hidden');

    if (!error && data && data.length > 0) {
      allNews = data.map(item => ({
        ...item,
        cover_image: getSafeImageUrl(item.cover_image)
      }));

      renderHeroBlock(allNews);
      renderNews(allNews);
      setupBreakingNews(allNews);
    } else {
      document.getElementById('news-grid').innerHTML = `<div class="col-span-full py-16 text-center text-slate-400 font-mono text-xs">Chưa có bài viết trong cơ sở dữ liệu. Hãy chạy kịch bản cào tin mới!</div>`;
    }
  } catch (err) {
    console.error("Lỗi:", err);
    const loadingEl = document.getElementById('loading-state');
    if (loadingEl) loadingEl.classList.add('hidden');
  }
}

function setupBreakingNews(list) {
  const breaking = list.find(item => item.is_breaking) || list[0];
  if (breaking) {
    document.getElementById('breaking-ticker').innerText = `[${breaking.location}] ${breaking.title}`;
    document.getElementById('breaking-ticker').onclick = () => openArticleDetail(breaking.id);
  }
}

function renderHeroBlock(list) {
  if (list.length === 0) return;
  const main = list[0];
  document.getElementById('hero-main-img').src = main.cover_image;
  document.getElementById('hero-main-title').innerText = main.title;
  document.getElementById('hero-main-summary').innerText = main.summary;
  document.getElementById('hero-main-cat').innerText = categoryNames[main.category] || main.category;
  document.getElementById('hero-main-loc').innerText = `📍 ${main.location}`;

  const sides = list.slice(1, 3);
  document.getElementById('hero-side-container').innerHTML = sides.map(item => `
    <div onclick="openArticleDetail(${item.id})" class="flex-1 bg-white rounded-2xl sm:rounded-3xl overflow-hidden border border-slate-200/90 shadow-xs hover:shadow-md transition p-3.5 sm:p-4 cursor-pointer flex flex-col justify-between group">
      <div class="flex gap-3 items-start">
        <img src="${item.cover_image}" class="w-20 h-16 sm:w-24 sm:h-20 rounded-xl sm:rounded-2xl object-cover shrink-0 border border-slate-100 group-hover:scale-105 transition duration-300" onerror="handleImgError(this)">
        <div>
          <span class="text-[9px] font-mono font-bold text-brand-red uppercase block mb-1">${categoryNames[item.category] || item.category}</span>
          <h4 class="font-bold text-xs text-slate-900 leading-snug line-clamp-2 group-hover:text-brand-red transition">${item.title}</h4>
        </div>
      </div>
      <div class="text-[10px] font-mono text-slate-400 pt-2 border-t border-slate-100 mt-2 flex justify-between items-center">
        <span>📍 ${item.location}</span>
        <span class="text-brand-darkRed font-bold">Xem chi tiết &rarr;</span>
      </div>
    </div>
  `).join('');
}

function openHeroMain() {
  if (allNews.length > 0) openArticleDetail(allNews[0].id);
}

function renderNews(list) {
  const grid = document.getElementById('news-grid');
  document.getElementById('news-count').innerText = `${list.length} tin bài`;

  if (list.length === 0) {
    grid.innerHTML = `<div class="col-span-full py-12 text-center text-slate-400 font-mono text-xs">Không tìm thấy tin bài nào khớp với bộ lọc.</div>`;
    return;
  }

  grid.innerHTML = list.map(item => `
    <article onclick="openArticleDetail(${item.id})" class="bg-white rounded-2xl sm:rounded-3xl border border-slate-200/90 overflow-hidden shadow-xs hover:shadow-md transition flex flex-col justify-between group cursor-pointer">
      <div>
        <div class="aspect-[16/10] bg-slate-100 overflow-hidden relative border-b border-slate-100">
          <img src="${item.cover_image}" alt="${item.title}" class="w-full h-full object-cover group-hover:scale-105 transition duration-400" onerror="handleImgError(this)">
          <span class="absolute top-2.5 left-2.5 px-2.5 py-0.5 rounded-md text-[10px] font-bold font-mono bg-slate-900/80 text-white uppercase backdrop-blur-xs">
            ${categoryNames[item.category] || item.category}
          </span>
          <span class="absolute bottom-2 left-2 px-2.5 py-0.5 rounded-md text-[10px] font-semibold bg-white/90 text-slate-800 shadow-xs backdrop-blur-xs">
            📍 ${item.location}
          </span>
        </div>

        <div class="p-4 sm:p-5">
          <span class="text-[10px] font-mono text-slate-400 uppercase font-semibold block mb-1.5">${item.source_name}</span>
          <h3 class="font-bold text-xs sm:text-sm text-slate-900 leading-snug line-clamp-2 group-hover:text-brand-red transition mb-2">
            ${item.title}
          </h3>
          <p class="text-xs text-slate-500 line-clamp-3 leading-relaxed font-normal">
            ${item.summary}
          </p>
        </div>
      </div>

      <div class="p-4 sm:p-5 pt-0 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-400 mt-1 pt-2.5">
        <span class="text-brand-darkRed font-semibold group-hover:underline">Chi tiết vụ việc &rarr;</span>
      </div>
    </article>
  `).join('');
}

// Chuyển sang màn hình đọc chi tiết toàn văn (không dùng popup)
function openArticleDetail(id) {
  const item = allNews.find(n => n.id === id);
  if (!item) return;

  document.getElementById('catalog-view').classList.add('hidden');
  document.getElementById('article-detail-view').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });

  document.getElementById('detail-breadcrumb-cat').innerText = categoryNames[item.category] || item.category;
  document.getElementById('detail-category-badge').innerText = categoryNames[item.category] || item.category;
  document.getElementById('detail-location-badge').innerText = `Địa bàn: ${item.location}`;
  document.getElementById('detail-source-badge').innerText = `Nguồn: ${item.source_name}`;
  document.getElementById('detail-article-title').innerText = item.title;
  document.getElementById('detail-article-summary').innerText = item.summary;
  document.getElementById('detail-article-img').src = item.cover_image;
  document.getElementById('detail-article-content').innerHTML = item.content_html;
  document.getElementById('detail-source-name').innerText = item.source_name;
  document.getElementById('detail-source-link').href = item.source_url || '#';

  const related = allNews.filter(n => n.id !== item.id && (n.category === item.category || n.location === item.location)).slice(0, 4);
  document.getElementById('related-news-container').innerHTML = (related.length > 0 ? related : allNews.slice(0, 4)).map(rel => `
    <div onclick="openArticleDetail(${rel.id})" class="flex gap-3 items-start cursor-pointer group pb-3 border-b border-slate-100 last:border-b-0">
      <img src="${rel.cover_image}" class="w-16 h-14 rounded-xl object-cover shrink-0 border border-slate-100 group-hover:scale-105 transition" onerror="handleImgError(this)">
      <div>
        <h5 class="font-bold text-xs text-slate-800 leading-snug line-clamp-2 group-hover:text-brand-red transition">${rel.title}</h5>
        <span class="text-[10px] font-mono text-slate-400 block mt-1">📍 ${rel.location}</span>
      </div>
    </div>
  `).join('');
}

function showCatalogView() {
  document.getElementById('article-detail-view').classList.add('hidden');
  document.getElementById('catalog-view').classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function filterCategory(cat) {
  currentCategory = cat;
  document.querySelectorAll('.cat-pill').forEach(btn => {
    if (btn.getAttribute('data-cat') === cat) {
      btn.className = "cat-pill active px-3.5 py-1.5 rounded-full bg-brand-lightRed text-brand-darkRed border border-red-200 shrink-0 transition font-bold";
    } else {
      btn.className = "cat-pill px-3.5 py-1.5 rounded-full text-slate-600 hover:text-slate-900 hover:bg-slate-100 shrink-0 transition border border-transparent font-semibold";
    }
  });
  applyFilters();
}

function filterLocation(loc) {
  currentLocation = loc;
  applyFilters();
}

function handleSearch() {
  applyFilters();
}

function applyFilters() {
  const q = document.getElementById('search-input')?.value.toLowerCase().trim() || '';

  const filtered = allNews.filter(item => {
    const matchCat = (currentCategory === 'ALL') || (item.category === currentCategory);
    const matchLoc = (currentLocation === 'ALL') || (item.location.toLowerCase().includes(currentLocation.toLowerCase()));
    const matchText = (!q) || item.title.toLowerCase().includes(q) || item.location.toLowerCase().includes(q) || item.summary.toLowerCase().includes(q);
    return matchCat && matchLoc && matchText;
  });

  renderNews(filtered);
}

// Đăng ký PWA Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then(reg => console.log('PWA Service Worker đã bật:', reg.scope))
      .catch(err => console.error('PWA Lỗi:', err));
  });
}

window.addEventListener('DOMContentLoaded', fetchCrimeNews);
