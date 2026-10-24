// Raport wydatków — panel w aplikacji + pobieranie PDF (obliczenia robi moduł Pythona przez api.php)
(function () {
    const STATUS = { complete: 'pełny', in_progress: 'w toku', partial_start: 'niepełny' };
    const section = el('reportSection');
    const out = el('repOutput');
    const msg = el('repMessage');

    const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const pct = (v, signed = true) => v === null || v === undefined ? '–'
        : (signed && Math.abs(v) < 0.05 ? '0,0%' : (signed && v > 0 ? '+' : '') + v.toFixed(1).replace('.', ',') + '%');

    function showMessage(text, isError) {
        msg.textContent = text || '';
        msg.classList.toggle('hidden', !text);
        msg.classList.toggle('error', !!isError);
    }

    // Zakres dat z wyboru "Zakres": ostatnie N miesięcy / od początku / własny
    function getRange() {
        const v = el('repRange').value;
        const today = new Date();
        if (v === 'custom') return { from: el('repFrom').value, to: el('repTo').value };
        if (v === 'all') return { from: '', to: '' };
        const start = new Date(today.getFullYear(), today.getMonth() - parseInt(v, 10), 1);
        return { from: iso(start), to: iso(today) };
    }

    function params() {
        const r = getRange();
        return { granularity: el('repGran').value, from: r.from, to: r.to };
    }

    function card(label, value, hint) {
        return `<div class="rep-card" ${hint ? `title="${escapeHtml(hint)}"` : ''}><span>${label}</span><strong>${value}</strong></div>`;
    }

    function renderChart(r) {
        const max = Math.max(...r.buckets.map(b => b.total), 1);
        const st = r.stats;
        const line = (val, cls) => val == null ? '' :
            `<div class="rep-line ${cls}" style="bottom:${val / max * 100}%"></div>`;
        const legendLine = (val, cls, label) => val == null ? '' :
            `<span class="swl ${cls}"></span> ${label}: ${formatCurrency(val)}`;
        const bars = r.buckets.map(b => `
            <div class="rep-col" title="${escapeHtml(b.label)}: ${formatCurrency(b.total)} (${STATUS[b.status]})">
                <div class="rep-val">${formatCurrency(b.total)}</div>
                <div class="rep-bar ${b.complete ? '' : 'partial'}" style="height:${b.total / max * 100}%"></div>
                <div class="rep-lbl">${escapeHtml(b.label)}</div>
            </div>`).join('');
        return `<div class="rep-chart"><div class="rep-plot"><div class="rep-area">${line(st.mean, 'mean')}${line(st.median, 'median')}<div class="rep-bars">${bars}</div></div></div></div>
                <p class="rep-legend"><span class="sw full"></span> pełny okres <span class="sw partial"></span> okres w toku / niepełny (nie wchodzi do średniej)
                ${legendLine(st.mean, 'mean', 'średnia')} ${legendLine(st.median, 'median', 'mediana')}</p>`;
    }

    function renderReport(r) {
        if (!r.buckets.length) {
            out.innerHTML = '';
            showMessage((r.warnings && r.warnings[0]) || 'Brak danych do raportu w wybranym zakresie.', false);
            return;
        }
        const st = r.stats, sm = r.summary;
        const na = 'brak <small>(za mało okresów)</small>';
        const notes = [...(r.warnings || []), ...st.notes];

        out.innerHTML = `
            <div class="rep-cards">
                ${card('Suma w zakresie', formatCurrency(sm.total_range))}
                ${card(`Średnia na okres (${st.n} pełnych)`, st.mean != null ? formatCurrency(st.mean) : na, 'Średnia wymaga min. 2 pełnych okresów')}
                ${card('Mediana', st.median != null ? formatCurrency(st.median) : na, 'Mediana wymaga min. 3 pełnych okresów')}
                ${card('Najmniej / najwięcej', st.min ? `${formatCurrency(st.min.value)} / ${formatCurrency(st.max.value)}` : '–')}
                ${card('Koszt miesięczny teraz', formatCurrency(sm.monthly_now))}
                ${card('Prognoza roczna', formatCurrency(sm.yearly_projection))}
            </div>
            ${renderChart(r)}
            <h3>Zestawienie okresów</h3>
            <table class="rep-table"><thead><tr><th>Okres</th><th>Suma</th><th>Zmiana vs poprzedni</th><th>Status</th></tr></thead><tbody>
                ${r.buckets.map(b => `<tr><td>${escapeHtml(b.label)}</td><td>${formatCurrency(b.total)}</td>
                    <td class="${b.change_pct > 0 ? 'up' : b.change_pct < 0 ? 'down' : ''}">${pct(b.change_pct)}</td><td>${STATUS[b.status]}</td></tr>`).join('')}
            </tbody></table>
            <h3>Kategorie</h3>
            <table class="rep-table"><thead><tr><th>Kategoria</th><th>Suma w zakresie</th><th>Udział</th><th>Koszt mies. (aktywne)</th></tr></thead><tbody>
                ${r.categories.map(c => `<tr><td>${escapeHtml(c.name)}</td><td>${formatCurrency(c.total)}</td><td>${pct(c.share, false)}</td><td>${formatCurrency(c.monthly_now)}</td></tr>`).join('')}
            </tbody></table>
            ${r.insights.length ? `<h3>Jak obniżyć wydatki</h3><ul class="rep-tips">${r.insights.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>` : ''}
            ${notes.length ? `<ul class="rep-notes">${notes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}</ul>` : ''}`;
        showMessage('');
    }

    function generateLocalReport() {
        const active = subs.filter(subscription => subscription.active);
        const monthlyTotal = active.reduce((sum, subscription) => sum + toMonthly(subscription.cost, subscription.period), 0);
        const byCategory = new Map();
        active.forEach(subscription => {
            const category = subscription.category || 'Bez kategorii';
            byCategory.set(category, (byCategory.get(category) || 0) + toMonthly(subscription.cost, subscription.period));
        });
        const categoryRows = [...byCategory.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([name, total]) => `<tr><td>${escapeHtml(name)}</td><td>${formatCurrency(total)}</td><td>${monthlyTotal ? (total / monthlyTotal * 100).toFixed(1).replace('.', ',') : '0,0'}%</td></tr>`)
            .join('');
        const subscriptionRows = active
            .slice()
            .sort((a, b) => b.cost - a.cost)
            .map(subscription => `<tr><td>${escapeHtml(subscription.name)}</td><td>${formatCurrency(subscription.cost)}</td><td>${subscription.period === 'yearly' ? 'Roczny' : 'Miesięczny'}</td><td>${escapeHtml(subscription.category || 'Bez kategorii')}</td></tr>`)
            .join('');

        out.innerHTML = `
            <p>Raport na podstawie aktualnie zapisanych, aktywnych subskrypcji. Dane są przechowywane tylko w tej przeglądarce; wersja GitHub Pages nie przechowuje historii płatności.</p>
            <div class="rep-cards">
                ${card('Aktywne subskrypcje', String(active.length))}
                ${card('Koszt miesięczny', formatCurrency(monthlyTotal))}
                ${card('Prognoza roczna', formatCurrency(monthlyTotal * 12))}
            </div>
            <h3>Koszt miesięczny według kategorii</h3>
            <table class="rep-table"><thead><tr><th>Kategoria</th><th>Koszt mies.</th><th>Udział</th></tr></thead><tbody>
                ${categoryRows || '<tr><td colspan="3">Brak aktywnych subskrypcji.</td></tr>'}
            </tbody></table>
            <h3>Aktywne subskrypcje</h3>
            <table class="rep-table"><thead><tr><th>Nazwa</th><th>Koszt</th><th>Okres</th><th>Kategoria</th></tr></thead><tbody>
                ${subscriptionRows || '<tr><td colspan="4">Brak aktywnych subskrypcji.</td></tr>'}
            </tbody></table>`;
        showMessage('');
    }

    async function generate() {
        if (STATIC_MODE) {
            generateLocalReport();
            return;
        }
        const p = params();
        if (el('repRange').value === 'custom' && p.from && p.to && p.from > p.to) {
            showMessage('Data początkowa jest późniejsza niż końcowa.', true);
            return;
        }
        showMessage('Generowanie raportu…');
        out.innerHTML = '';
        const res = await requestAPI({ action: 'report_data', ...p });
        if (res.success) renderReport(res.report);
        else showMessage(res.message || 'Nie udało się wygenerować raportu.', true);
    }

    async function downloadPdf() {
        if (STATIC_MODE) {
            window.print();
            return;
        }
        showMessage('Generowanie PDF…');
        try {
            const response = await fetch('api.php', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: 'report_pdf', ...params() })
            });
            if ((response.headers.get('Content-Type') || '').includes('application/pdf')) {
                const url = URL.createObjectURL(await response.blob());
                const a = document.createElement('a');
                a.href = url; a.download = `raport_wydatkow_${iso(new Date())}.pdf`;
                document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
                showMessage('');
            } else {
                const data = await response.json();
                showMessage(data.message || 'Nie udało się wygenerować PDF.', true);
            }
        } catch (e) {
            showMessage('Błąd połączenia z serwerem.', true);
        }
    }

    // Zdarzenia
    el('reportToggleBtn').addEventListener('click', () => {
        const nowVisible = section.classList.toggle("hidden") === false;
        if (nowVisible) {
            if (STATIC_MODE) {
                el('repGran').closest('label').hidden = true;
                el('repRange').closest('label').hidden = true;
                el('repCustom').classList.add('hidden');
                el('repGenerateBtn').textContent = 'Odśwież';
                el('repPdfBtn').textContent = 'Drukuj / zapisz PDF';
            }
            section.scrollIntoView({ behavior: 'smooth' });
            generate();
        }
    });
    el('repRange').addEventListener('change', () => el('repCustom').classList.toggle('hidden', el('repRange').value !== 'custom'));
    el('repGenerateBtn').addEventListener('click', generate);
    el('repPdfBtn').addEventListener('click', downloadPdf);
    el('repGran').addEventListener('change', generate);
    el('logoutBtn').addEventListener('click', () => { out.innerHTML = ''; showMessage(''); section.classList.add('hidden'); });

    if (typeof flatpickr !== 'undefined') {
        const opts = { dateFormat: 'Y-m-d', allowInput: true, disableMobile: true };
        flatpickr(el('repFrom'), opts);
        flatpickr(el('repTo'), opts);
    }
})();
