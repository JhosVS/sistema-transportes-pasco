(() => {
    const $ = (id) => document.getElementById(id);
    const cfg = $('cfg').dataset;
    const M = JSON.parse($('metricas').textContent);
    const AZUL = '#0d6efd', ROJO = '#dc3545', AMARILLO = '#ffc107';
    const BASE = { responsive: true, maintainAspectRatio: false };
    const eje = (t, max) => ({ min: 0, max, title: { display: true, text: t } });

    /* ---------- Evaluación ---------- */
    const DISP = M.dispersion;
    const puntos = (alta) => DISP.filter((d) => !!d.alta_real === alta)
        .map((d) => ({ x: d.probabilidad * 100, y: d.ocupacion_real * 100 }));

    const chartDisp = new Chart($('chartDisp'), {
        type: 'scatter',
        data: { datasets: [
            { label: 'Alta ocupación', backgroundColor: ROJO + 'AA', data: puntos(true) },
            { label: 'No alta', backgroundColor: AZUL + 'AA', data: puntos(false) },
            { type: 'line', label: '70% real', data: [{ x: 0, y: 70 }, { x: 100, y: 70 }],
              borderColor: '#212529', borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0 },
            { type: 'line', label: 'Umbral', data: [], borderColor: AMARILLO, borderWidth: 2, pointRadius: 0 },
        ] },
        options: { ...BASE, plugins: { legend: { position: 'bottom' } },
            scales: { x: eje('Probabilidad predicha (%)', 100), y: eje('Ocupación real (%)', 105) } },
    });

    const chartCalib = new Chart($('chartCalib'), {
        type: 'scatter',
        data: { datasets: [
            { label: 'Modelo', showLine: true, borderColor: AMARILLO, backgroundColor: AMARILLO, borderWidth: 3, pointRadius: 5,
              data: M.calibracion.prob_predicha.map((x, i) => ({ x: x * 100, y: M.calibracion.frecuencia_real[i] * 100 })) },
            { label: 'Calibración perfecta', showLine: true, borderColor: '#6c757d', borderDash: [6, 4], pointRadius: 0,
              data: [{ x: 0, y: 0 }, { x: 100, y: 100 }] },
        ] },
        options: { ...BASE, plugins: { legend: { position: 'bottom' } },
            scales: { x: eje('Probabilidad predicha (%)', 100), y: eje('Frecuencia real (%)', 100) } },
    });

    const imp = M.importancia_variables.slice(0, 10);
    const chartImp = new Chart($('chartImp'), {
        type: 'bar',
        data: { labels: imp.map((d) => d.variable),
                datasets: [{ data: imp.map((d) => d.importancia), backgroundColor: AMARILLO, borderColor: '#212529', borderWidth: 1 }] },
        options: { ...BASE, indexAxis: 'y', plugins: { legend: { display: false } } },
    });

    function aplicarUmbral() {
        const t = parseFloat($('umbral').value);
        $('umbralTxt').textContent = t.toFixed(2);
        let vn = 0, fp = 0, fn = 0, vp = 0;
        DISP.forEach((d) => {
            const pred = d.probabilidad >= t;
            if (d.alta_real) pred ? vp++ : fn++; else pred ? fp++ : vn++;
        });
        const n = DISP.length, pct = (x) => (x * 100).toFixed(1) + '%';
        $('kpiAcc').textContent = pct((vn + vp) / n);
        $('kpiPrec').textContent = pct(vp + fp ? vp / (vp + fp) : 0);
        $('kpiRec').textContent = pct(vp + fn ? vp / (vp + fn) : 0);
        const celda = (id, v, ok) => {
            $(id).innerHTML = `<div class="fs-4 fw-bold">${v}</div><div class="small">${(v / n * 100).toFixed(1)}%</div>`;
            $(id).style.background = ok ? 'rgba(25,135,84,.18)' : 'rgba(220,53,69,.18)';
        };
        celda('cmVN', vn, true); celda('cmFP', fp, false); celda('cmFN', fn, false); celda('cmVP', vp, true);
        chartDisp.data.datasets[3].data = [{ x: t * 100, y: 0 }, { x: t * 100, y: 100 }];
        chartDisp.update('none');
    }
    $('umbral').addEventListener('input', aplicarUmbral);
    aplicarUmbral();

    document.querySelectorAll('#tabsPred [data-bs-toggle="tab"]').forEach((b) =>
        b.addEventListener('shown.bs.tab', () => [chartDisp, chartCalib, chartImp].forEach((c) => c.resize())));

    /* ---------- Reentrenar ---------- */
    $('btnRe').addEventListener('click', async (e) => {
        const btn = e.currentTarget, msg = $('msgRe'), texto = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Entrenando...';
        msg.className = 'alert alert-info small mx-3';
        msg.textContent = 'Entrenando con los datos actuales...';
        try {
            const resp = await fetch(cfg.reentrenar, { method: 'POST' });
            const r = await resp.json();
            if (!resp.ok) throw new Error(r.error || 'Error al reentrenar');
            msg.className = 'alert small mx-3 alert-' + (r.aceptado ? 'success' : 'warning');
            msg.textContent = r.aceptado ? `Modelo actualizado con ${r.filas} viajes. AUC: ${r.auc}.`
                : `El modelo nuevo (AUC ${r.auc}) no mejoró al actual (${r.auc_anterior}); se conserva el anterior.`;
            setTimeout(() => location.reload(), 2500);
        } catch (ex) {
            msg.className = 'alert alert-danger small mx-3';
            msg.textContent = ex.message;
            btn.disabled = false;
            btn.innerHTML = texto;
        }
    });

    /* ---------- Calendario de calor ---------- */
    const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    const hoy = new Date();
    let anio = hoy.getFullYear(), mes = hoy.getMonth(), dias = {};

    function colores(p) {
        if (p == null) return ['#f8f9fa', '#adb5bd'];
        if (p >= 70) return [ROJO, '#fff'];
        if (p >= 50) return [AMARILLO, '#000'];
        if (p >= 30) return ['#fff3cd', '#664d03'];
        return ['#cfe2ff', '#052c65'];
    }

    function sugerencia(p) {
        return p >= 70 ? 'Considerar bus extra o ajustar precio' : (p < 15 ? 'Considerar una promoción' : 'Operación normal');
    }

    function detalle(k) {
        const x = dias[k], el = $('calDetalle');
        if (!x || !x.salidas.length) { el.textContent = `${k}: sin salidas para esta ruta.`; return; }
        el.innerHTML = `<div class="fw-semibold mb-1">${k}${x.feriado ? ' · feriado' : ''}</div>
            <table class="table table-sm mb-0 small"><thead><tr><th>Hora</th><th>Bus</th><th>Prob.</th><th>Sugerencia</th></tr></thead><tbody>` +
            x.salidas.map((s) => `<tr><td>${s.hora}</td><td>${s.placa}</td><td><strong>${s.prob}%</strong></td><td>${sugerencia(s.prob)}</td></tr>`).join('') +
            '</tbody></table>';
    }

    async function cargarCalendario() {
        const mm = `${anio}-${String(mes + 1).padStart(2, '0')}`;
        $('calMes').textContent = `${MESES[mes]} ${anio}`;
        $('calError').classList.add('d-none');
        try {
            const r = await fetch(`${cfg.calendario}?id_ruta=${$('calRuta').value}&mes=${mm}`);
            const d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error al cargar el calendario');
            dias = d.dias;
            let html = '<div class="cal-vacio"></div>'.repeat(d.primer_dia);
            for (let n = 1; n <= d.total_dias; n++) {
                const k = `${mm}-${String(n).padStart(2, '0')}`, x = dias[k];
                const [bg, fg] = colores(x ? x.max : null);
                html += `<div class="cal-dia" data-k="${k}"
                    style="background:${bg};color:${fg};cursor:${x && x.salidas.length ? 'pointer' : 'default'}">
                    <div class="d-flex justify-content-between" style="font-size:.7rem"><span>${n}</span><span>${x && x.feriado ? '●' : ''}</span></div>
                    <div class="fw-bold text-center">${x && x.max != null ? Math.round(x.max) + '%' : ''}</div></div>`;
            }
            $('calGrid').innerHTML = html;
            $('calGrid').querySelectorAll('.cal-dia').forEach((c) => c.onclick = () => detalle(c.dataset.k));
            $('calDetalle').textContent = 'Toca un día para ver sus salidas.';
        } catch (e) {
            $('calError').textContent = e.message;
            $('calError').classList.remove('d-none');
        }
    }

    const mover = (delta) => () => {
        mes += delta;
        if (mes < 0) { mes = 11; anio--; } else if (mes > 11) { mes = 0; anio++; }
        cargarCalendario();
    };
    $('calRuta').onchange = cargarCalendario;
    $('calPrev').onclick = mover(-1);
    $('calNext').onclick = mover(1);
    cargarCalendario();
})();