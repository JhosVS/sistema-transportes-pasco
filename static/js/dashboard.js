/* Dashboard: pide los datos en JSON a /admin/dashboard/api/* y dibuja los gráficos. */
(() => {
    const cfg = document.getElementById('cfg').dataset;
    const $ = (id) => document.getElementById(id);
    const fmt = new Intl.NumberFormat('es-PE');
    const soles = new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN', maximumFractionDigits: 0 });
    const PALETA = ['#ffc107', '#212529', '#fd7e14', '#198754', '#0dcaf0', '#6c757d'];
    const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
    const BASE = { responsive: true, maintainAspectRatio: false };
    const graficos = {};
    const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);

    const iso = (f) => `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, '0')}-${String(f.getDate()).padStart(2, '0')}`;

    async function api(url, params) {
        const r = await fetch(url + '?' + new URLSearchParams(params));
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || 'Error al consultar los datos');
        return d;
    }

    function dibujar(id, config) {
        if (graficos[id]) graficos[id].destroy();
        graficos[id] = new Chart($(id), config);
    }

    function vacio(id, hay) {   // si no hay datos, el gráfico queda en blanco
        if (!hay && graficos[id]) { graficos[id].destroy(); delete graficos[id]; }
        return hay;
    }

    function error(msg) {
        $('error').textContent = msg;
        $('error').classList.toggle('d-none', !msg);
    }

    /* ---------- KPIs ---------- */
    function kpi(titulo, valor, detalle, icono, color) {
        return `<div class="col-12 col-sm-6 col-xl-4 col-xxl-2">
          <div class="card border-0 shadow-sm rounded-3 h-100"><div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <span class="text-muted small fw-semibold">${titulo}</span>
              <span class="bg-${color} bg-opacity-10 text-${color} rounded-circle p-2"><i class="bi ${icono}"></i></span>
            </div>
            <h4 class="fw-bold text-dark mt-1 mb-0">${valor}</h4>
            <div class="text-muted" style="font-size:.75rem">${detalle}</div>
          </div></div></div>`;
    }

    function renderKpis(k) {
        $('kpis').innerHTML = [
            kpi('Pasajeros', fmt.format(k.pasajeros), `${fmt.format(k.viajes)} viajes realizados`, 'bi-ticket-perforated', 'warning'),
            kpi('Ocupación', k.ocupacion == null ? '–' : k.ocupacion + '%', 'de los asientos disponibles', 'bi-pie-chart', 'primary'),
            kpi('Ingresos', soles.format(k.ingresos), `Pasajes ${soles.format(k.ing_pasajes)} · Encom. ${soles.format(k.ing_encomiendas)}`, 'bi-currency-dollar', 'success'),
            kpi('Margen parcial', soles.format(k.margen), `Ingresos menos mantenimiento (${soles.format(k.costo_mant)})`, 'bi-cash-stack', 'info'),
            kpi('Puntualidad', k.puntualidad == null ? '–' : k.puntualidad + '%', `Retraso promedio ${k.retraso_prom ?? '–'} min (≤15 min = puntual)`, 'bi-clock-history', 'success'),
            kpi('Cancelaciones', fmt.format(k.cancelados), 'viajes cancelados', 'bi-x-octagon', 'danger'),
        ].join('');
    }

    /* ---------- Gráficos ---------- */
    function gSerie(datos) {
        if (!vacio('g-serie', datos.length)) return;
        dibujar('g-serie', {
            type: 'bar',
            data: {
                labels: datos.map((d) => d.periodo),
                datasets: [
                    { label: 'Pasajeros', data: datos.map((d) => d.pasajeros), backgroundColor: PALETA[0], yAxisID: 'y', borderRadius: 3 },
                    { label: 'Ingresos (S/)', type: 'line', yAxisID: 'y1', tension: 0.25,
                      data: datos.map((d) => d.ingresos), borderColor: PALETA[1], backgroundColor: PALETA[1], pointRadius: 2 },
                ],
            },
            options: { ...BASE, interaction: { mode: 'index', intersect: false },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Pasajeros' } },
                    y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Soles' } },
                } },
        });
    }

    function gEstado(obj) {
        const labels = Object.keys(obj);
        if (!vacio('g-estado', labels.length)) return;
        dibujar('g-estado', {
            type: 'doughnut',
            data: { labels, datasets: [{ data: labels.map((l) => obj[l]), backgroundColor: ['#198754', '#dc3545', '#6c757d'], borderWidth: 0 }] },
            options: { ...BASE, cutout: '65%', plugins: { legend: { position: 'bottom' } } },
        });
    }

    function gSemana(datos) {
        if (!vacio('g-semana', datos.length)) return;
        dibujar('g-semana', {
            type: 'bar',
            data: { labels: datos.map((d) => DIAS[d.dia]), datasets: [{ label: 'Ocupación (%)', data: datos.map((d) => d.ocupacion), backgroundColor: PALETA[0], borderRadius: 3 }] },
            options: { ...BASE, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } },
        });
    }

    function gRutas(datos) {
        if (!vacio('g-rutas', datos.length)) return;
        dibujar('g-rutas', {
            type: 'bar',
            data: { labels: datos.map((d) => d.ruta), datasets: [{ label: 'Pasajeros', data: datos.map((d) => d.pasajeros), backgroundColor: PALETA[2], borderRadius: 3 }] },
            options: { ...BASE, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { y: { ticks: { font: { size: 9 } } } } },
        });
    }

    function gEdad(datos) {
        if (!vacio('g-edad', datos.length)) return;
        dibujar('g-edad', {
            type: 'doughnut',
            data: { labels: datos.map((d) => d.grupo), datasets: [{ data: datos.map((d) => d.pasajeros), backgroundColor: PALETA, borderWidth: 0 }] },
            options: { ...BASE, cutout: '55%', plugins: { legend: { position: 'right' } } },
        });
    }

    function gPagos(datos) {
        if (!vacio('g-pagos', datos.length)) return;
        dibujar('g-pagos', {
            type: 'doughnut',
            data: { labels: datos.map((d) => cap(d.metodo)), datasets: [{ data: datos.map((d) => d.ingresos), backgroundColor: PALETA, borderWidth: 0 }] },
            options: { ...BASE, cutout: '55%', plugins: { legend: { position: 'right' } } },
        });
    }

    /* ---------- Tablas ---------- */
    function tFlota(datos) {
        const badge = (e) => `<span class="badge bg-${e === 'Disponible' ? 'success' : (e === 'Mantenimiento' ? 'danger' : 'secondary')}">${e}</span>`;
        $('t-flota').innerHTML = `<thead class="table-light"><tr><th>Placa</th><th>Tipo</th><th>Asientos</th>
            <th>Viajes</th><th>Km</th><th>Mant.</th><th>Días fuera</th><th>Estado</th></tr></thead><tbody>` +
            datos.map((d) => `<tr><td class="fw-semibold">${d.placa}</td><td>${d.tipo}</td><td>${d.asientos}</td>
              <td>${fmt.format(d.viajes)}</td><td>${fmt.format(d.km)}</td><td>${d.mantenimientos}</td>
              <td>${d.dias_fuera}</td><td>${badge(d.estado)}</td></tr>`).join('') + '</tbody>';
    }

    function tPrediccion(p) {
        const el = $('prediccion');
        if (!p.disponible) {
            el.innerHTML = '<div class="p-4 text-center text-muted small">El modelo aún no está entrenado. Entrénalo desde Predicción de Demanda.</div>';
        } else if (!p.viajes.length) {
            el.innerHTML = '<div class="p-4 text-center text-muted small">No hay viajes programados próximos.</div>';
        } else {
            el.innerHTML = '<table class="table table-hover align-middle mb-0 small"><tbody>' + p.viajes.map((v) => {
                const c = v.prob >= 70 ? 'danger' : (v.prob >= 40 ? 'warning' : 'secondary');
                return `<tr><td><div class="fw-semibold">${v.ruta}</div><div class="text-muted">${v.fecha} · ${v.placa}</div></td>
                  <td style="width:38%"><div class="d-flex align-items-center gap-2">
                  <div class="progress flex-grow-1" style="height:8px"><div class="progress-bar bg-${c}" style="width:${v.prob}%"></div></div>
                  <strong>${v.prob}%</strong></div></td></tr>`;
            }).join('') + '</tbody></table>';
        }
    }

    /* ---------- Carga ---------- */
    const rango = () => ({ desde: $('desde').value, hasta: $('hasta').value });

    async function cargarSerie() {
        const s = await api(cfg.serie, { ...rango(), agrupar: $('agrupar').value });
        gSerie(s.datos);
    }

    async function cargarTodo() {
        error('');
        try {
            const d = await api(cfg.todo, rango());
            renderKpis(d.kpis);
            gEstado(d.estado_flota);
            gSemana(d.semana);
            gRutas(d.rutas);
            gEdad(d.edad);
            gPagos(d.pagos);
            tFlota(d.flota);
            tPrediccion(d.prediccion);
            await cargarSerie();
        } catch (e) {
            error(e.message);
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const hoy = new Date();
        const hace = (n) => new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - n);
        $('hasta').value = iso(hoy);
        $('desde').value = iso(hace(29));

        $('btn-aplicar').addEventListener('click', cargarTodo);
        $('agrupar').addEventListener('change', () => cargarSerie().catch((e) => error(e.message)));

        const agrupacion = { 30: 'dia', 90: 'semana', 365: 'mes' };
        document.querySelectorAll('.atajo').forEach((b) => b.addEventListener('click', () => {
            const dias = Number(b.dataset.dias);
            $('desde').value = iso(hace(dias - 1));
            $('hasta').value = iso(hoy);
            $('agrupar').value = agrupacion[dias];
            cargarTodo();
        }));

        cargarTodo();
    });
})();