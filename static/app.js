// State
    let currentSites = [];
    let currentReferences = []; // list of string refs
    let selectedReferences = new Set(); // set of selected refs
    let currentResults = [];
    let isSearching = false;
    let isBatchRunning = false;
    let searchStartTime = 0;
    let timerInterval = null;
    let searchAbortController = null;

    // DOM Elements
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const btnClearSearch = document.getElementById('btnClearSearch');
    const btnSearch = document.getElementById('btnSearch');
    const btnStopSearch = document.getElementById('btnStopSearch');
    const btnStatusStopSearch = document.getElementById('btnStatusStopSearch');
    const searchStatusSection = document.getElementById('searchStatusSection');
    const searchStatusText = document.getElementById('searchStatusText');
    const searchTimer = document.getElementById('searchTimer');
    const sitePillsContainer = document.getElementById('sitePillsContainer');
    const resultsGrid = document.getElementById('resultsGrid');
    const emptyState = document.getElementById('emptyState');
    const noMatchesState = document.getElementById('noMatchesState');
    const totalMatchesBadge = document.getElementById('totalMatchesBadge');
    const resultsSummaryText = document.getElementById('resultsSummaryText');
    const filterRefSelect = document.getElementById('filterRefSelect');
    const filterStoreSelect = document.getElementById('filterStoreSelect');
    const sortSelect = document.getElementById('sortSelect');
    const btnExportCsv = document.getElementById('btnExportCsv');
    const btnSyncGdoc = document.getElementById('btnSyncGdoc');
    const btnSyncSiteGdoc = document.getElementById('btnSyncSiteGdoc');

    // References DOM Elements
    const refSelectionBadge = document.getElementById('refSelectionBadge');
    const referencesChipsContainer = document.getElementById('referencesChipsContainer');
    const btnSearchSelectedRefs = document.getElementById('btnSearchSelectedRefs');
    const btnSearchSelectedText = document.getElementById('btnSearchSelectedText');
    const btnSelectAllRefs = document.getElementById('btnSelectAllRefs');
    const btnDeselectAllRefs = document.getElementById('btnDeselectAllRefs');
    const btnSyncRefGdoc = document.getElementById('btnSyncRefGdoc');
    const inlineAddRefInput = document.getElementById('inlineAddRefInput');
    const btnInlineAddRef = document.getElementById('btnInlineAddRef');
    const btnToggleRefEditor = document.getElementById('btnToggleRefEditor');
    const refEditorToggleText = document.getElementById('refEditorToggleText');
    const refEditorContainer = document.getElementById('refEditorContainer');
    const rawRefsTextarea = document.getElementById('rawRefsTextarea');
    const btnSaveRefs = document.getElementById('btnSaveRefs');
    const btnCancelRefEditor = document.getElementById('btnCancelRefEditor');
    const btnResetRefsDefault = document.getElementById('btnResetRefsDefault');

    // Sites Inline DOM Elements
    const heroSitesCount = document.getElementById('heroSitesCount');
    const quickSiteBadge = document.getElementById('quickSiteBadge');
    const inlineAddUrl = document.getElementById('inlineAddUrl');
    const btnInlineAdd = document.getElementById('btnInlineAdd');
    const btnToggleEditor = document.getElementById('btnToggleEditor');
    const inlineEditorContainer = document.getElementById('inlineEditorContainer');
    const rawSitesTextarea = document.getElementById('rawSitesTextarea');
    const btnSaveRawSites = document.getElementById('btnSaveRawSites');
    const btnCancelEditor = document.getElementById('btnCancelEditor');
    const btnResetToGdoc = document.getElementById('btnResetToGdoc');
    const btnSelectAll = document.getElementById('btnSelectAll');
    const btnDeselectAll = document.getElementById('btnDeselectAll');
    const siteFilterInput = document.getElementById('siteFilterInput');
    const quickSiteChips = document.getElementById('quickSiteChips');

    // Modal DOM Elements
    const sitesModal = document.getElementById('sitesModal');
    const btnOpenSitesModal = document.getElementById('btnOpenSitesModal');
    const btnCloseSitesModal = document.getElementById('btnCloseSitesModal');
    const btnCloseModalFooter = document.getElementById('btnCloseModalFooter');
    const headerSiteCountBadge = document.getElementById('headerSiteCountBadge');
    const modalSiteCount = document.getElementById('modalSiteCount');
    const sitesTableBody = document.getElementById('sitesTableBody');
    
    // Tab switching
    const tabBtnList = document.getElementById('tabBtnList');
    const tabBtnAdd = document.getElementById('tabBtnAdd');
    const tabBtnBulk = document.getElementById('tabBtnBulk');
    const tabContentList = document.getElementById('tabContentList');
    const tabContentAdd = document.getElementById('tabContentAdd');
    const tabContentBulk = document.getElementById('tabContentBulk');

    const addSiteForm = document.getElementById('addSiteForm');
    const btnRunBulkImport = document.getElementById('btnRunBulkImport');
    const bulkImportTextarea = document.getElementById('bulkImportTextarea');

    // Initialize
    
        // --- PROTECTED MARKETPLACES 1-CLICK LAUNCHPAD DYNAMIC UPDATER ---
    function updateProtectedLaunchpad(query) {
      const searchInputEl = document.getElementById('searchInput');
      const activeQ = (query || (searchInputEl ? searchInputEl.value : '') || '').trim();
      const badge = document.getElementById('launchpadActiveQueryBadge');
      if (badge) {
        badge.textContent = activeQ ? `Query: ${activeQ}` : 'Active Query: All Markets';
      }
      
      const qEncoded = encodeURIComponent(activeQ || 'Rolex');
      const qPlus = encodeURIComponent(activeQ || 'Rolex').replace(/%20/g, '+');

      const btnC24 = document.getElementById('lpBtnChrono24');
      if (btnC24) btnC24.href = `https://www.chrono24.com/search/index.htm?query=${qEncoded}&dosearch=true`;

      const btnRF = document.getElementById('lpBtnRolexForums');
      if (btnRF) btnRF.href = `https://www.google.com/search?q=site:rolexforums.com+${encodeURIComponent('"' + (activeQ || 'Rolex') + '"')}`;

      const btnWC = document.getElementById('lpBtnWatchCharts');
      if (btnWC) btnWC.href = `https://watchcharts.com/search?q=${qEncoded}`;

      const btnAvi = document.getElementById('lpBtnAviAndCo');
      if (btnAvi) btnAvi.href = `https://www.aviandco.com/catalogsearch/result/?q=${qEncoded}`;

      const btnBezel = document.getElementById('lpBtnBezel');
      if (btnBezel) btnBezel.href = `https://shop.getbezel.com/search?q=${qEncoded}`;

      const btnWP = document.getElementById('lpBtnWatchPatrol');
      if (btnWP) btnWP.href = `https://www.watchpatrol.net/?query=${qEncoded}`;
    }

    async function init() {
      fetchVersion();
      await fetchSites();
      await fetchReferences();
      setupEventListeners();
    }

    async function fetchVersion() {
      try {
        const res = await fetch('/api/version', { credentials: 'same-origin' });
        if (res.ok) {
          const data = await res.json();
          const badge = document.getElementById('headerVersionBadge');
          if (badge && data) {
            badge.textContent = `v${data.version || '2.7.1'} • ${data.revision || 'live'}`;
            badge.title = `Cloud Run Service: ${data.service || 'watch-finder'} | Revision: ${data.revision || 'live'}`;
          }
        }
      } catch (err) {
        console.error('Failed to fetch version info:', err);
      }
    }

    async function fetchSites() {
      try {
        const res = await fetch('/api/sites', { credentials: 'same-origin' });
        const data = await res.json();
        currentSites = Array.isArray(data) ? data : (data.sites || []);
        currentSites.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base', numeric: true }));
        updateSitesUI();
        updateProtectedLaunchpad('');
      } catch (err) {
        console.error('Failed to load sites:', err);
      }
    }

    async function fetchReferences() {
      try {
        const res = await fetch('/api/references');
        const data = await res.json();
        currentReferences = Array.isArray(data) ? data : (data.references || []);
        // Default: select all references
        selectedReferences = new Set(); // None selected by default
        updateReferencesUI();
      } catch (err) {
        console.error('Failed to load references:', err);
      }
    }

    const refFilterInput = document.getElementById('refFilterInput');

    function updateReferencesUI() {
      const total = currentReferences.length;
      const selectedCount = selectedReferences.size;
      
      refSelectionBadge.textContent = `${selectedCount} of ${total} active`;
      btnSearchSelectedText.textContent = `Search Active References (${selectedCount})`;
      btnSearchSelectedRefs.disabled = selectedCount === 0;
      btnSearchSelectedRefs.classList.toggle('opacity-50', selectedCount === 0);
      btnSearchSelectedRefs.classList.toggle('cursor-not-allowed', selectedCount === 0);

      referencesChipsContainer.innerHTML = '';

      // Update Filter by Ref select
      const currentSelectedRef = filterRefSelect.value;
      filterRefSelect.innerHTML = '<option value="all">All References</option>';

      const filterText = (refFilterInput ? refFilterInput.value || '' : '').toLowerCase();

      currentReferences.forEach(ref => {
        const opt = document.createElement('option');
        opt.value = ref;
        opt.textContent = `Ref: ${ref}`;
        filterRefSelect.appendChild(opt);

        if (filterText && !ref.toLowerCase().includes(filterText)) {
          return;
        }

        const isSelected = selectedReferences.has(ref);

        const chip = document.createElement('div');
        chip.className = `group px-2 py-0.5 rounded-lg text-[11px] font-mono font-medium flex items-center gap-1.5 transition cursor-pointer select-none ${
          isSelected 
            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30' 
            : 'bg-slate-800/40 text-slate-500 border border-slate-700/40 hover:text-slate-300'
        }`;
        
        chip.innerHTML = `
          <i class="fa-solid ${isSelected ? 'fa-circle-check text-amber-400' : 'fa-circle text-slate-600'} text-[9px]"></i>
          <span>${ref}</span>
          <div class="flex items-center gap-1 pl-1 border-l border-slate-700/60 ml-0.5" onclick="event.stopPropagation()">
            <button type="button" class="btn-single-search text-slate-500 hover:text-amber-300 p-0.5 transition" title="Search single reference: ${ref}">
              <i class="fa-solid fa-magnifying-glass text-[9px]"></i>
            </button>
            <button type="button" class="btn-remove-ref text-slate-500 hover:text-rose-400 p-0.5 transition" title="Delete reference">
              <i class="fa-solid fa-xmark text-[9px]"></i>
            </button>
          </div>
        `;

        // Click anywhere on chip to toggle selection (mimicking websites chips)
        chip.addEventListener('click', () => {
          if (selectedReferences.has(ref)) {
            selectedReferences.delete(ref);
          } else {
            selectedReferences.add(ref);
          }
          updateReferencesUI();
        });

        // 1-Click Search single ref
        chip.querySelector('.btn-single-search').addEventListener('click', (e) => {
          e.stopPropagation();
          searchInput.value = ref;
          btnClearSearch.classList.remove('hidden');
          executeSearch(ref);
        });

        // Delete ref
        chip.querySelector('.btn-remove-ref').addEventListener('click', (e) => {
          e.stopPropagation();
          deleteRef(ref);
        });

        referencesChipsContainer.appendChild(chip);
      });

      filterRefSelect.value = currentSelectedRef || 'all';
    }

    function updateSitesUI() {
      const total = currentSites.length;
      const enabledCount = currentSites.filter(s => s.enabled).length;
      headerSiteCountBadge.textContent = `${enabledCount}/${total}`;
      heroSitesCount.textContent = enabledCount;
      quickSiteBadge.textContent = `${enabledCount} of ${total} active`;
      modalSiteCount.textContent = total;

      const selectedFilter = filterStoreSelect.value;
      filterStoreSelect.innerHTML = '<option value="all">All Websites</option>';
      currentSites.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = s.name;
        filterStoreSelect.appendChild(opt);
      });
      filterStoreSelect.value = selectedFilter || 'all';

      renderQuickChips();
      renderSitesTable();
    }

    function renderQuickChips() {
      quickSiteChips.innerHTML = '';
      const filterText = (siteFilterInput.value || '').toLowerCase();
      
      currentSites.forEach(s => {
        if (filterText && !s.name.toLowerCase().includes(filterText) && !s.url.toLowerCase().includes(filterText)) {
          return;
        }

        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = `px-2 py-0.5 rounded-lg text-[11px] font-medium flex items-center gap-1 transition ${
          s.enabled 
            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30' 
            : 'bg-slate-800/40 text-slate-500 border border-slate-700/40 hover:text-slate-300'
        }`;
        chip.innerHTML = `
          <i class="fa-solid ${s.enabled ? 'fa-circle-check text-amber-400' : 'fa-circle text-slate-600'} text-[9px]"></i>
          <span>${s.name}</span>
        `;
        chip.addEventListener('click', () => toggleSiteStatus(s.id, !s.enabled));
        quickSiteChips.appendChild(chip);
      });
    }

    function renderSitesTable() {
      sitesTableBody.innerHTML = '';
      currentSites.forEach(site => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-800/40 transition';
        tr.innerHTML = `
          <td class="py-3 px-4">
            <input type="checkbox" ${site.enabled ? 'checked' : ''} onchange="toggleSiteStatus('${site.id}', this.checked)" class="rounded bg-slate-800 border-slate-700 text-amber-500 focus:ring-amber-500 h-4 w-4">
          </td>
          <td class="py-3 px-4 font-semibold text-white">${site.name}</td>
          <td class="py-3 px-4 font-mono text-[11px] text-slate-400">
            <a href="${site.url}" target="_blank" class="hover:text-amber-400 flex items-center gap-1">
              <span>${site.url}</span>
              <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
            </a>
          </td>
          <td class="py-3 px-4"><span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">${site.category || 'Dealer'}</span></td>
          <td class="py-3 px-4 text-right">
            <button onclick="deleteSite('${site.id}')" class="text-rose-400 hover:text-rose-300 p-1 rounded hover:bg-rose-500/10 transition" title="Delete Website">
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </td>
        `;
        sitesTableBody.appendChild(tr);
      });
    }

    async function toggleSiteStatus(siteId, enabled) {
      try {
        await fetch(`/api/sites/${siteId}/toggle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled })
        });
        const site = currentSites.find(s => s.id === siteId);
        if (site) site.enabled = enabled;
        updateSitesUI();
        updateProtectedLaunchpad('');
      } catch (err) {
        console.error('Failed to toggle site:', err);
      }
    }

    async function deleteSite(siteId) {
      if (!confirm('Are you sure you want to remove this website from your search list?')) return;
      try {
        await fetch(`/api/sites/${siteId}`, { method: 'DELETE' });
        currentSites = currentSites.filter(s => s.id !== siteId);
        updateSitesUI();
        updateProtectedLaunchpad('');
      } catch (err) {
        console.error('Failed to delete site:', err);
      }
    }

    // Stop Search Execution
    
    
        function finalizeSitePills(siteMatchesMap) {
      if (!sitePillsContainer) return;
      const enabledSites = currentSites.filter(s => s.enabled);
      
      enabledSites.forEach(s => {
        const pill = document.getElementById(`pill-${s.id}`);
        if (!pill) return;
        const matchCount = siteMatchesMap ? (siteMatchesMap[s.id] || 0) : 0;
        
        if (matchCount > 0) {
          pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 flex items-center gap-1.5 shadow-sm shadow-emerald-500/20';
          pill.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i><span>${s.name}</span><span class="bg-emerald-500 text-slate-950 text-[10px] font-extrabold px-1.5 py-0.2 rounded-full">${matchCount}</span>`;
        } else {
          pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-900/60 border border-slate-800 text-slate-500 flex items-center gap-1.5';
          pill.innerHTML = `<i class="fa-solid fa-circle-dot text-slate-600 text-[9px]"></i><span>${s.name}</span>`;
        }
      });
    }

    function stopSearch() {
      if (searchAbortController) {
        searchAbortController.abort();
        searchAbortController = null;
      }
      
      clearInterval(timerInterval);
      isSearching = false;
      isBatchRunning = false;
      
      btnSearch.classList.remove('hidden');
      btnStopSearch.classList.add('hidden');
      btnStatusStopSearch.classList.add('hidden');
      document.getElementById('searchSpinner').classList.add('hidden');
    }

    // Single Query Execution
    async function executeSearch(query) {
      if (!query) return;
      updateProtectedLaunchpad(query);
      if (isSearching || isBatchRunning) {
        stopSearch();
      }

      isSearching = true;
      isBatchRunning = false;
      searchAbortController = new AbortController();

      btnSearch.classList.add('hidden');
      btnStopSearch.classList.remove('hidden');
      btnStatusStopSearch.classList.remove('hidden');
      document.getElementById('searchSpinner').classList.remove('hidden');

      emptyState.classList.add('hidden');
      noMatchesState.classList.add('hidden');
      searchStatusSection.classList.remove('hidden');
      resultsGrid.innerHTML = '';
      if (resultsTableBody) resultsTableBody.innerHTML = '';
      if (marketSnapshotBar) marketSnapshotBar.classList.add('hidden');
      currentResults = [];
      totalMatchesBadge.textContent = '0';
      if (filterRefSelect) filterRefSelect.value = 'all';
      if (filterStoreSelect) filterStoreSelect.value = 'all';

      const enabledSites = currentSites.filter(s => s.enabled);
      searchStatusText.textContent = `Searching ${enabledSites.length} websites in parallel for "${query}"...`;
      resultsSummaryText.textContent = `Searching ${enabledSites.length} websites...`;

      sitePillsContainer.innerHTML = '';
      enabledSites.forEach(s => {
        const pill = document.createElement('div');
        pill.id = `pill-${s.id}`;
        pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-900/60 border border-slate-800 text-slate-400 flex items-center gap-1.5 transition-all';
        pill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-slate-600"></span><span>${s.name}</span>`;
        sitePillsContainer.appendChild(pill);
      });

      searchStartTime = Date.now();
      timerInterval = setInterval(() => {
        const elapsed = ((Date.now() - searchStartTime) / 1000).toFixed(1);
        searchTimer.textContent = `${elapsed}s`;
      }, 100);

      const siteMatchesMap = {};

      try {
        const res = await fetch(`/api/search/stream?query=${encodeURIComponent(query)}`, {
          credentials: 'same-origin',
          signal: searchAbortController.signal
        });

        if (!res.ok) {
          throw new Error(`Server returned HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop();

          for (const chunk of chunks) {
            const lines = chunk.split('\n');
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              try {
                const event = JSON.parse(line.slice(6));
                if (event.type === 'site_result') {
                  const sr = event.data;
                  const matches = (sr.products || []).length;
                  const pill = document.getElementById(`pill-${sr.site_id}`);
                  if (matches > 0) {
                    siteMatchesMap[sr.site_id] = matches;
                    if (pill) {
                      pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 flex items-center gap-1.5 shadow-sm shadow-emerald-500/20 animate-pulse';
                      pill.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i><span>${sr.site_name}</span><span class="bg-emerald-500 text-slate-950 text-[10px] font-extrabold px-1.5 py-0.2 rounded-full">${matches}</span>`;
                    }
                    sr.products.forEach(p => {
                      p.matched_reference = query;
                      p.site_name = sr.site_name;
                      p.site_url = sr.site_url;
                      currentResults.push(p);
                      appendResultCard(p);
                    });
                    totalMatchesBadge.textContent = currentResults.length;
                    resultsSummaryText.textContent = `Streaming results: Found ${currentResults.length} matching items so far...`;
                  } else if (pill) {
                    pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-900/40 border border-slate-800/60 text-slate-500 flex items-center gap-1.5';
                    pill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-slate-700"></span><span>${sr.site_name || 'Store'}</span>`;
                  }
                } else if (event.type === 'done') {
                  clearInterval(timerInterval);
                  const finalElapsed = ((Date.now() - searchStartTime) / 1000).toFixed(1);
                  searchTimer.textContent = `${finalElapsed}s`;
                  totalMatchesBadge.textContent = currentResults.length;
                  resultsSummaryText.textContent = `Found ${currentResults.length} matching items across ${enabledSites.length} websites in ${finalElapsed}s for "${query}"`;
                  searchStatusText.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-check-circle"></i> Search Complete!</span> Found ${currentResults.length} matching watch listings.`;
                  populateFilterDropdowns();
                  updateMarketSnapshot(currentResults, query);
                  if (currentResults.length === 0) {
                    noMatchesState.classList.remove('hidden');
                  }
                }
              } catch (err) {
                console.error('SSE Chunk parse error:', err);
              }
            }
          }
        }
      } catch (e) {
        if (e.name !== 'AbortError') {
          console.error('Search error:', e);
          alert('Search encountered an error: ' + e.message);
        }
      } finally {
        isSearching = false;
        searchAbortController = null;
        btnSearch.classList.remove('hidden');
        btnStopSearch.classList.add('hidden');
        btnStatusStopSearch.classList.add('hidden');
        document.getElementById('searchSpinner').classList.add('hidden');
        finalizeSitePills(siteMatchesMap);
      }
    }

    // Batch Search Execution for Selected References
    async function executeSelectedBatchSearch() {
      const selectedList = Array.from(selectedReferences);
      if (selectedList.length === 0) {
        alert('Please select at least one watch reference from your watchlist.');
        return;
      }

      if (isSearching || isBatchRunning) {
        stopSearch();
      }

      isBatchRunning = true;
      isSearching = false;
      searchAbortController = new AbortController();

      btnSearch.classList.add('hidden');
      btnStopSearch.classList.remove('hidden');
      btnStatusStopSearch.classList.remove('hidden');
      document.getElementById('searchSpinner').classList.remove('hidden');

      emptyState.classList.add('hidden');
      noMatchesState.classList.add('hidden');
      searchStatusSection.classList.remove('hidden');
      resultsGrid.innerHTML = '';
      if (resultsTableBody) resultsTableBody.innerHTML = '';
      if (marketSnapshotBar) marketSnapshotBar.classList.add('hidden');
      currentResults = [];
      totalMatchesBadge.textContent = '0';
      if (filterRefSelect) filterRefSelect.value = 'all';
      if (filterStoreSelect) filterStoreSelect.value = 'all';

      const enabledSites = currentSites.filter(s => s.enabled);
      const totalRefs = selectedList.length;
      const siteCumulativeMatches = {};

      sitePillsContainer.innerHTML = '';
      enabledSites.forEach(s => {
        const pill = document.createElement('div');
        pill.id = `pill-${s.id}`;
        pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-900/60 border border-slate-800 text-slate-400 flex items-center gap-1.5 transition-all';
        pill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-slate-600"></span><span>${s.name}</span>`;
        sitePillsContainer.appendChild(pill);
      });

      searchStartTime = Date.now();
      timerInterval = setInterval(() => {
        const elapsed = ((Date.now() - searchStartTime) / 1000).toFixed(1);
        searchTimer.textContent = `${elapsed}s`;
      }, 100);

      try {
        for (let i = 0; i < totalRefs; i++) {
          if (!isBatchRunning) break;
          const ref = selectedList[i];
          updateProtectedLaunchpad(ref);
          
          searchStatusText.innerHTML = `Searching Reference <strong class="text-amber-400">${i + 1}/${totalRefs}</strong>: <span class="font-mono font-bold text-white bg-slate-800 px-2 py-0.5 rounded">${ref}</span> across ${enabledSites.length} websites...`;
          resultsSummaryText.textContent = `Searching ${i + 1} of ${totalRefs} references... (${currentResults.length} matches found so far)`;

          const res = await fetch('/api/search', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: ref }),
            signal: searchAbortController.signal
          });

          if (res.ok) {
            const data = await res.json();
            const prods = data.all_products || [];
            prods.forEach(p => { p.matched_reference = ref; });
            currentResults.push(...prods);

            if (data.site_results) {
              data.site_results.forEach(sr => {
                const siteMatches = (sr.products || []).length;
                if (siteMatches > 0) {
                  siteCumulativeMatches[sr.site_id] = (siteCumulativeMatches[sr.site_id] || 0) + siteMatches;
                  const pill = document.getElementById(`pill-${sr.site_id}`);
                  if (pill) {
                    pill.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 flex items-center gap-1.5 shadow-sm shadow-emerald-500/20';
                    pill.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i><span>${sr.site_name}</span><span class="bg-emerald-500 text-slate-950 text-[10px] font-extrabold px-1.5 py-0.2 rounded-full">${siteCumulativeMatches[sr.site_id]}</span>`;
                  }
                }
              });
            }

            totalMatchesBadge.textContent = currentResults.length;
            renderResults();
          }
        }

        clearInterval(timerInterval);
        const finalElapsed = ((Date.now() - searchStartTime) / 1000).toFixed(1);
        searchTimer.textContent = `${finalElapsed}s`;
        searchStatusText.innerHTML = `<span class="text-emerald-400 font-bold"><i class="fa-solid fa-check-circle"></i> Batch Search Complete!</span> Found ${currentResults.length} matches across ${totalRefs} selected references in ${finalElapsed}s.`;
        resultsSummaryText.textContent = `Found ${currentResults.length} matching items across ${totalRefs} references in ${finalElapsed}s`;

        if (currentResults.length === 0) {
          noMatchesState.classList.remove('hidden');
        }

        populateFilterDropdowns();
      } catch (e) {
        if (e.name !== 'AbortError') {
          console.error('Batch search error:', e);
        }
      } finally {
        isBatchRunning = false;
        searchAbortController = null;
        btnSearch.classList.remove('hidden');
        btnStopSearch.classList.add('hidden');
        btnStatusStopSearch.classList.add('hidden');
        document.getElementById('searchSpinner').classList.add('hidden');
        finalizeSitePills(siteCumulativeMatches);
      }
    }

    function populateFilterDropdowns() {
      // 1. Populate Store Filter with matching stores
      const storeCounts = {};
      currentResults.forEach(p => {
        const store = p.site_name || 'Dealer';
        storeCounts[store] = (storeCounts[store] || 0) + 1;
      });

      const currentStoreVal = filterStoreSelect ? filterStoreSelect.value : 'all';
      if (filterStoreSelect) {
        filterStoreSelect.innerHTML = '<option value="all">All Websites</option>';
        Object.keys(storeCounts).sort().forEach(store => {
          const opt = document.createElement('option');
          opt.value = store;
          opt.textContent = `${store} (${storeCounts[store]})`;
          filterStoreSelect.appendChild(opt);
        });
        filterStoreSelect.value = storeCounts[currentStoreVal] ? currentStoreVal : 'all';
      }

      // 2. Populate Reference Filter with matching refs (if batch search)
      const refCounts = {};
      currentResults.forEach(p => {
        if (p.matched_reference) {
          refCounts[p.matched_reference] = (refCounts[p.matched_reference] || 0) + 1;
        }
      });

      if (filterRefSelect) {
        const currentRefVal = filterRefSelect.value;
        filterRefSelect.innerHTML = '<option value="all">All References</option>';
        if (Object.keys(refCounts).length > 0) {
          Object.keys(refCounts).sort().forEach(ref => {
            const opt = document.createElement('option');
            opt.value = ref;
            opt.textContent = `${ref} (${refCounts[ref]})`;
            filterRefSelect.appendChild(opt);
          });
          filterRefSelect.value = refCounts[currentRefVal] ? currentRefVal : 'all';
        }
      }
    }

    
// View Switcher State
    let currentViewMode = 'grid'; // 'grid' or 'table'
    const btnViewGrid = document.getElementById('btnViewGrid');
    const btnViewTable = document.getElementById('btnViewTable');
    const resultsTableContainer = document.getElementById('resultsTableContainer');
    const resultsTableBody = document.getElementById('resultsTableBody');
    const marketSnapshotBar = document.getElementById('marketSnapshotBar');

    if (btnViewGrid && btnViewTable) {
      btnViewGrid.addEventListener('click', () => setViewMode('grid'));
      btnViewTable.addEventListener('click', () => setViewMode('table'));
    }

    function setViewMode(mode) {
      currentViewMode = mode;
      if (mode === 'grid') {
        btnViewGrid.className = 'px-2.5 py-1 rounded-lg bg-amber-500 text-slate-950 flex items-center gap-1.5 transition font-bold';
        btnViewTable.className = 'px-2.5 py-1 rounded-lg text-slate-400 hover:text-white flex items-center gap-1.5 transition';
        resultsGrid.classList.remove('hidden');
        resultsTableContainer.classList.add('hidden');
      } else {
        btnViewTable.className = 'px-2.5 py-1 rounded-lg bg-amber-500 text-slate-950 flex items-center gap-1.5 transition font-bold';
        btnViewGrid.className = 'px-2.5 py-1 rounded-lg text-slate-400 hover:text-white flex items-center gap-1.5 transition';
        resultsGrid.classList.add('hidden');
        resultsTableContainer.classList.remove('hidden');
      }
    }

    function extractNumericPrice(priceStr) {
      if (!priceStr || priceStr.toLowerCase().includes('inquire')) return null;
      const clean = priceStr.split('(')[0];
      const match = clean.match(/[\d,]+(?:\.\d{2})?/);
      if (match) {
        const num = parseFloat(match[0].replace(/,/g, ''));
        return isNaN(num) ? null : num;
      }
      return null;
    }

    function copyListingDetails(title, price, store, url, btn) {
      const formatted = `${title} — ${price} at ${store}\n${url}`;
      navigator.clipboard.writeText(formatted).then(() => {
        const originalHtml = btn.innerHTML;
        btn.classList.remove('bg-slate-800', 'text-slate-300');
        btn.classList.add('bg-emerald-600', 'text-white', 'border-emerald-400');
        btn.innerHTML = '<i class="fa-solid fa-check"></i> <span class="text-[11px] font-bold">Copied!</span>';
        setTimeout(() => {
          btn.innerHTML = originalHtml;
          btn.classList.remove('bg-emerald-600', 'text-white', 'border-emerald-400');
          btn.classList.add('bg-slate-800', 'text-slate-300');
        }, 2000);
      }).catch(err => {
        console.error('Clipboard error:', err);
      });
    }

    function updateMarketSnapshot(items, activeQuery = '') {
      if (!marketSnapshotBar) return;
      const pricedItems = items.map(p => ({
        ...p,
        numericPrice: extractNumericPrice(p.price)
      })).filter(p => p.numericPrice !== null && p.numericPrice > 300);

      if (pricedItems.length === 0) {
        marketSnapshotBar.classList.add('hidden');
        return;
      }

      marketSnapshotBar.classList.remove('hidden');
      pricedItems.sort((a, b) => a.numericPrice - b.numericPrice);

      const lowest = pricedItems[0];
      const highest = pricedItems[pricedItems.length - 1];
      const medianIndex = Math.floor(pricedItems.length / 2);
      const median = pricedItems.length % 2 === 0
        ? (pricedItems[medianIndex - 1].numericPrice + pricedItems[medianIndex].numericPrice) / 2
        : pricedItems[medianIndex].numericPrice;

      const uniqueStores = new Set(items.map(p => p.site_name || 'Dealer')).size;

      const qEl = document.getElementById('marketSnapshotQuery');
      if (qEl && activeQuery) {
        qEl.textContent = `Market Intelligence for "${activeQuery}"`;
      }

      document.getElementById('statLowestPrice').textContent = `$${lowest.numericPrice.toLocaleString()}`;
      document.getElementById('statLowestDealer').textContent = lowest.site_name || 'Dealer';

      document.getElementById('statMedianPrice').textContent = `$${Math.round(median).toLocaleString()}`;

      document.getElementById('statHighestPrice').textContent = `$${highest.numericPrice.toLocaleString()}`;
      document.getElementById('statHighestDealer').textContent = highest.site_name || 'Dealer';

      document.getElementById('statTotalPriced').textContent = `${pricedItems.length} priced`;
      document.getElementById('statDealersCount').textContent = `across ${uniqueStores} dealers`;
    }

    function createCardElement(p) {
      const card = document.createElement('div');
      card.className = 'glass-card rounded-2xl overflow-hidden flex flex-col justify-between hover:border-amber-500/40 transition hover:shadow-xl group animate-fade-in';
      
      const scorePercent = Math.round((p.score || 0.8) * 100);
      const scoreBadgeColor = scorePercent >= 90 ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30';

      const imageHtml = p.image 
        ? `<div class="w-full h-48 bg-slate-900 overflow-hidden relative"><img src="${p.image}" alt="${p.title}" loading="lazy" decoding="async" class="w-full h-full object-contain p-2 group-hover:scale-105 transition duration-300" onerror="this.parentElement.style.display='none'"></div>`
        : `<div class="w-full h-24 bg-gradient-to-br from-slate-900 to-slate-950 flex items-center justify-center text-slate-700 text-3xl"><i class="fa-solid fa-clock"></i></div>`;

      card.innerHTML = `
        <div>
          ${imageHtml}
          <div class="p-5 flex flex-col gap-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-[11px] font-bold text-amber-400 tracking-wider uppercase">${p.site_name || 'Dealer'}</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${scoreBadgeColor}">${scorePercent}% Match</span>
            </div>

            ${p.matched_reference ? `
              <div class="self-start">
                <span class="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-mono text-[10px] font-bold border border-amber-500/30 flex items-center gap-1">
                  <i class="fa-solid fa-tag text-[8px]"></i> Ref: ${p.matched_reference}
                </span>
              </div>
            ` : ''}
            
            <h4 class="text-sm font-bold text-white line-clamp-2 hover:text-amber-300 transition" title="${p.title}">
              <a href="${p.url}" target="_blank" rel="noopener noreferrer">${p.title}</a>
            </h4>
            
            ${p.vendor ? `<span class="text-xs text-slate-400">Maker: <strong class="text-slate-300">${p.vendor}</strong></span>` : ''}
          </div>
        </div>

        <div class="p-5 pt-0 border-t border-slate-800/40 mt-3 flex items-center justify-between gap-2">
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Price</span>
            <span class="text-base font-extrabold text-amber-400 font-mono">${p.price || 'Inquire'}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <button class="btn-copy-card px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition flex items-center gap-1.5 border border-slate-700/60" title="1-Click Copy Listing Summary">
              <i class="fa-solid fa-copy text-amber-400"></i>
              <span class="text-[11px]">Copy</span>
            </button>
            <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-amber-500 text-slate-300 hover:text-slate-950 text-xs font-bold transition flex items-center gap-1.5 border border-slate-700/60">
              <span>View</span>
              <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>
          </div>
        </div>
      `;

      const copyBtn = card.querySelector('.btn-copy-card');
      if (copyBtn) {
        copyBtn.addEventListener('click', () => {
          copyListingDetails(p.title, p.price, p.site_name || 'Dealer', p.url, copyBtn);
        });
      }

      return card;
    }

    function createTableRowElement(p) {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-slate-900/60 transition';

      const scorePercent = Math.round((p.score || 0.8) * 100);
      const scoreBadgeColor = scorePercent >= 90 ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30';

      const imageHtml = p.image
        ? `<img src="${p.image}" alt="${p.title}" loading="lazy" class="w-10 h-10 object-contain rounded-lg bg-slate-900 border border-slate-800 p-0.5" onerror="this.style.display='none'">`
        : `<div class="w-10 h-10 rounded-lg bg-slate-900 flex items-center justify-center text-slate-600"><i class="fa-solid fa-clock"></i></div>`;

      tr.innerHTML = `
        <td class="p-3.5 text-center">${imageHtml}</td>
        <td class="p-3.5 font-bold text-white hover:text-amber-300">
          <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="line-clamp-1">${p.title}</a>
        </td>
        <td class="p-3.5 font-mono text-amber-400 font-semibold">${p.matched_reference || '—'}</td>
        <td class="p-3.5 text-slate-300 font-medium">${p.site_name || 'Dealer'}</td>
        <td class="p-3.5 font-mono font-extrabold text-amber-400 text-sm whitespace-nowrap">${p.price || 'Inquire'}</td>
        <td class="p-3.5 text-center">
          <span class="px-2 py-0.5 rounded-full text-[10px] font-bold border ${scoreBadgeColor}">${scorePercent}%</span>
        </td>
        <td class="p-3.5 text-right whitespace-nowrap">
          <div class="flex items-center justify-end gap-1.5">
            <button class="btn-copy-row px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition flex items-center gap-1 border border-slate-700/60" title="1-Click Copy Listing Summary">
              <i class="fa-solid fa-copy text-amber-400"></i>
              <span class="text-[10px]">Copy</span>
            </button>
            <a href="${p.url}" target="_blank" rel="noopener noreferrer" class="px-3 py-1 rounded-lg bg-slate-800 hover:bg-amber-500 text-slate-300 hover:text-slate-950 text-xs font-bold transition flex items-center gap-1 border border-slate-700/60">
              <span>View</span>
              <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
            </a>
          </div>
        </td>
      `;

      const copyBtn = tr.querySelector('.btn-copy-row');
      if (copyBtn) {
        copyBtn.addEventListener('click', () => {
          copyListingDetails(p.title, p.price, p.site_name || 'Dealer', p.url, copyBtn);
        });
      }

      return tr;
    }

    function appendResultCard(p, activeQuery = '') {
      if (noMatchesState) noMatchesState.classList.add('hidden');
      const card = createCardElement(p);
      resultsGrid.appendChild(card);

      if (resultsTableBody) {
        const row = createTableRowElement(p);
        resultsTableBody.appendChild(row);
      }

      updateMarketSnapshot(currentResults, activeQuery);
    }

    function renderResults() {
      resultsGrid.innerHTML = '';
      if (resultsTableBody) resultsTableBody.innerHTML = '';
      const filterRef = filterRefSelect.value;
      const filterStore = filterStoreSelect.value;
      const sortBy = sortSelect.value;

      let filtered = [...currentResults];

      if (filterRef !== 'all') {
        filtered = filtered.filter(p => p.matched_reference === filterRef);
      }

      if (filterStore !== 'all') {
        filtered = filtered.filter(p => p.site_name === filterStore);
      }

      if (sortBy === 'price_asc') {
        filtered.sort((a, b) => {
          const pa = extractNumericPrice(a.price);
          const pb = extractNumericPrice(b.price);
          if (pa === null && pb === null) return 0;
          if (pa === null) return 1;
          if (pb === null) return -1;
          return pa - pb;
        });
      } else if (sortBy === 'price_desc') {
        filtered.sort((a, b) => {
          const pa = extractNumericPrice(a.price);
          const pb = extractNumericPrice(b.price);
          if (pa === null && pb === null) return 0;
          if (pa === null) return 1;
          if (pb === null) return -1;
          return pb - pa;
        });
      } else if (sortBy === 'store') {
        filtered.sort((a, b) => (a.site_name || '').localeCompare(b.site_name || ''));
      } else if (sortBy === 'ref') {
        filtered.sort((a, b) => (a.matched_reference || '').localeCompare(b.matched_reference || ''));
      } else {
        filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
      }

      // Update Market Valuation Snapshot with active filtered listings
      updateMarketSnapshot(filtered);

      if (filtered.length === 0) {
        noMatchesState.classList.remove('hidden');
        if (marketSnapshotBar) marketSnapshotBar.classList.add('hidden');
        return;
      }

      noMatchesState.classList.add('hidden');

      filtered.forEach(p => {
        const card = createCardElement(p);
        resultsGrid.appendChild(card);
        if (resultsTableBody) {
          const row = createTableRowElement(p);
          resultsTableBody.appendChild(row);
        }
      });
    }

    function setupEventListeners() {
      searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        executeSearch(searchInput.value.trim());
      });

      btnStopSearch.addEventListener('click', stopSearch);
      btnStatusStopSearch.addEventListener('click', stopSearch);
      btnSearchSelectedRefs.addEventListener('click', executeSelectedBatchSearch);

      // Select All / Deselect All References
      btnSelectAllRefs.addEventListener('click', () => {
        selectedReferences = new Set(); // None selected by default
        updateReferencesUI();
      });

      btnDeselectAllRefs.addEventListener('click', () => {
        selectedReferences.clear();
        updateReferencesUI();
      });

      // Sync References from Google Doc
      btnSyncRefGdoc.addEventListener('click', async () => {
        try {
          btnSyncRefGdoc.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Syncing...';
          const res = await fetch('/api/references/sync-gdoc', { method: 'POST' });
          const data = await res.json();
          currentReferences = Array.isArray(data) ? data : (data.references || []);
          selectedReferences = new Set(); // None selected by default
          updateReferencesUI();
          alert(`Synced ${data.count} references from Google Doc!`);
        } catch (e) {
          alert(`Failed to sync references: ${e.message}`);
        } finally {
          btnSyncRefGdoc.innerHTML = '<i class="fa-brands fa-google-drive text-emerald-400"></i><span>Sync Doc</span>';
        }
      });

      searchInput.addEventListener('input', () => {
        updateProtectedLaunchpad(searchInput.value);
        updateProtectedLaunchpad(searchInput.value);
        btnClearSearch.classList.toggle('hidden', !searchInput.value);
      });

      btnClearSearch.addEventListener('click', () => {
        searchInput.value = '';
        btnClearSearch.classList.add('hidden');
        searchInput.focus();
      });

      // References Editor UI Listeners
      btnInlineAddRef.addEventListener('click', async () => {
        const ref = inlineAddRefInput.value.trim();
        if (!ref) return;
        try {
          const res = await fetch('/api/references/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reference: ref })
          });
          const data = await res.json();
          currentReferences = Array.isArray(data) ? data : (data.references || []);
          selectedReferences.add(ref);
          inlineAddRefInput.value = '';
          updateReferencesUI();
        } catch (e) {
          alert(e.message);
        }
      });

      inlineAddRefInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          btnInlineAddRef.click();
        }
      });

      btnToggleRefEditor.addEventListener('click', () => {
        refEditorContainer.classList.toggle('hidden');
        if (!refEditorContainer.classList.contains('hidden')) {
          rawRefsTextarea.value = currentReferences.join('\n');
          rawRefsTextarea.focus();
          refEditorToggleText.textContent = 'Hide Editor';
        } else {
          refEditorToggleText.textContent = 'Edit Multi-List';
        }
      });

      btnCancelRefEditor.addEventListener('click', () => {
        refEditorContainer.classList.add('hidden');
        refEditorToggleText.textContent = 'Edit Multi-List';
      });

      btnSaveRefs.addEventListener('click', async () => {
        const raw_text = rawRefsTextarea.value;
        try {
          const res = await fetch('/api/references', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text })
          });
          const data = await res.json();
          currentReferences = Array.isArray(data) ? data : (data.references || []);
          selectedReferences = new Set(); // None selected by default
          updateReferencesUI();
          refEditorContainer.classList.add('hidden');
          refEditorToggleText.textContent = 'Edit Multi-List';
        } catch (e) {
          alert(e.message);
        }
      });

      btnResetRefsDefault.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/references/sync-gdoc', { method: 'POST' });
          const data = await res.json();
          currentReferences = Array.isArray(data) ? data : (data.references || []);
          selectedReferences = new Set(); // None selected by default
          rawRefsTextarea.value = currentReferences.join('\n');
          updateReferencesUI();
        } catch (e) {
          alert(e.message);
        }
      });

      // Inline Quick Add Website
      btnInlineAdd.addEventListener('click', async () => {
        const url = inlineAddUrl.value.trim();
        if (!url) {
          alert('Please enter a website URL');
          return;
        }
        try {
          const res = await fetch('/api/sites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
          });
          if (res.ok) {
            inlineAddUrl.value = '';
            await fetchSites();
          } else {
            const err = await res.json();
            alert(`Error: ${err.detail || 'Could not add site'}`);
          }
        } catch (e) {
          alert(e.message);
        }
      });

      // Inline Full List Editor
      btnToggleEditor.addEventListener('click', async () => {
        inlineEditorContainer.classList.toggle('hidden');
        if (!inlineEditorContainer.classList.contains('hidden')) {
          const res = await fetch('/api/sites/raw');
          const data = await res.json();
          rawSitesTextarea.value = data.raw_text || '';
          rawSitesTextarea.focus();
        }
      });

      btnCancelEditor.addEventListener('click', () => {
        inlineEditorContainer.classList.add('hidden');
      });

      btnSaveRawSites.addEventListener('click', async () => {
        const raw_text = rawSitesTextarea.value;
        try {
          const res = await fetch('/api/sites/raw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_text })
          });
          const data = await res.json();
          alert(`Saved! Now searching across ${data.count} websites.`);
          inlineEditorContainer.classList.add('hidden');
          await fetchSites();
        } catch (e) {
          alert(`Failed to save: ${e.message}`);
        }
      });

      // Reset Websites to Google Doc
      btnResetToGdoc.addEventListener('click', syncFromGoogleDoc);
      btnSyncGdoc.addEventListener('click', syncFromGoogleDoc);
      if (btnSyncSiteGdoc) btnSyncSiteGdoc.addEventListener('click', syncFromGoogleDoc);

      async function syncFromGoogleDoc() {
        if (!confirm('Sync websites list directly from Google Drive document?')) return;
        try {
          btnSyncGdoc.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i> Syncing...';
          const res = await fetch('/api/sites/sync-gdoc', { method: 'POST' });
          const data = await res.json();
          alert(`Google Doc synced successfully! Loaded ${data.count} websites.`);
          await fetchSites();
        } catch (e) {
          alert(`Sync error: ${e.message}`);
        } finally {
          btnSyncGdoc.innerHTML = '<i class="fa-brands fa-google-drive text-emerald-400"></i><span class="hidden sm:inline">Sync Websites Doc</span>';
        }
      }

      // Quick Select / Deselect All Sites
      btnSelectAll.addEventListener('click', async () => {
        currentSites.forEach(s => { s.enabled = true; });
        updateSitesUI();
        updateProtectedLaunchpad('');
        try {
          await fetch('/api/sites/toggle-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: true })
          });
        } catch (e) {
          console.error('Failed to persist select-all:', e);
        }
      });

      btnDeselectAll.addEventListener('click', async () => {
        currentSites.forEach(s => { s.enabled = false; });
        updateSitesUI();
        updateProtectedLaunchpad('');
        try {
          await fetch('/api/sites/toggle-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: false })
          });
        } catch (e) {
          console.error('Failed to persist deselect-all:', e);
        }
      });

      siteFilterInput.addEventListener('input', renderQuickChips);
      if (refFilterInput) refFilterInput.addEventListener('input', updateReferencesUI);

      // Filters
      filterRefSelect.addEventListener('change', renderResults);
      filterStoreSelect.addEventListener('change', renderResults);
      sortSelect.addEventListener('change', renderResults);

      // Export CSV
      btnExportCsv.addEventListener('click', () => {
        const q = searchInput.value.trim() || 'batch_search';
        window.open(`/api/export/csv?query=${encodeURIComponent(q)}`, '_blank');
      });

      // Modal Open/Close
      btnOpenSitesModal.addEventListener('click', () => sitesModal.classList.remove('hidden'));
      btnCloseSitesModal.addEventListener('click', () => sitesModal.classList.add('hidden'));
      btnCloseModalFooter.addEventListener('click', () => sitesModal.classList.add('hidden'));

      tabBtnList.addEventListener('click', () => switchTab('list'));
      tabBtnAdd.addEventListener('click', () => switchTab('add'));
      tabBtnBulk.addEventListener('click', () => switchTab('bulk'));

      // Add Site Form
      addSiteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          url: document.getElementById('addSiteUrl').value.trim(),
          name: document.getElementById('addSiteName').value.trim(),
          category: document.getElementById('addSiteCategory').value.trim(),
          platform: document.getElementById('addSitePlatform').value,
        };

        try {
          const res = await fetch('/api/sites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          if (res.ok) {
            alert('Website added successfully!');
            addSiteForm.reset();
            await fetchSites();
            switchTab('list');
          } else {
            const err = await res.json();
            alert(`Error: ${err.detail || 'Could not add website'}`);
          }
        } catch (err) {
          alert(`Error: ${err.message}`);
        }
      });

      // Bulk Import Sites
      btnRunBulkImport.addEventListener('click', async () => {
        const text = bulkImportTextarea.value.trim();
        if (!text) {
          alert('Please paste some website URLs first.');
          return;
        }

        try {
          const res = await fetch('/api/sites/bulk', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, category: 'Dealer' })
          });
          const data = await res.json();
          alert(`Successfully imported ${data.added_count} websites!`);
          bulkImportTextarea.value = '';
          await fetchSites();
          switchTab('list');
        } catch (err) {
          alert(`Failed to import: ${err.message}`);
        }
      });
    }

    function switchTab(tab) {
      tabBtnList.className = tab === 'list' ? 'py-3 text-amber-400 border-b-2 border-amber-400 flex items-center gap-2' : 'py-3 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-2';
      tabBtnAdd.className = tab === 'add' ? 'py-3 text-amber-400 border-b-2 border-amber-400 flex items-center gap-2' : 'py-3 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-2';
      tabBtnBulk.className = tab === 'bulk' ? 'py-3 text-amber-400 border-b-2 border-amber-400 flex items-center gap-2' : 'py-3 text-slate-400 hover:text-slate-200 border-b-2 border-transparent flex items-center gap-2';

      tabContentList.classList.toggle('hidden', tab !== 'list');
      tabContentAdd.classList.toggle('hidden', tab !== 'add');
      tabContentBulk.classList.toggle('hidden', tab !== 'bulk');
    }

    window.addEventListener('DOMContentLoaded', init);