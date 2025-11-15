(function () {
    "use strict";

    const NUMBER_FORMAT = new Intl.NumberFormat("es-DO");
    const CURRENCY_FORMAT = new Intl.NumberFormat("es-DO", {
        style: "currency",
        currency: "DOP",
        minimumFractionDigits: 2,
    });

    const REPORT_CONFIG = {
        "total-sales": {
            endpoint: "/app/reportes/ventas-totales/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin" },
            cardValue: (data) => data?.total_sales_display ?? "—",
            summaryFields: {
                total: (data) => data?.total_sales_display ?? "—",
                cost: (data) => data?.total_cost_display ?? "—",
                profit: (data) => data?.total_profit_display ?? "—",
                discount: (data) => data?.total_discount_display ?? "—",
                tradein: (data) => data?.total_trade_in_display ?? "—",
                invoices: (data) => formatNumber(data?.ventas_display),
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.factura)}</td>
                    <td>${escapeHtml(row.cliente)}</td>
                    <td>${escapeHtml(row.fecha_display)}</td>
                    <td>${escapeHtml(row.subtotal_display)}</td>
                    <td>${escapeHtml(row.itbis_display)}</td>
                    <td>${escapeHtml(row.total_display)}</td>
                    <td>${escapeHtml(row.costo_display)}</td>
                    <td>${escapeHtml(row.ganancia_display)}</td>
                    <td>${escapeHtml(row.metodo_pago)}</td>
                    <td>${escapeHtml(row.descuento_display)}</td>
                    <td>${escapeHtml(row.trade_in_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron ventas para los filtros seleccionados.",
        },
        "sales-cost": {
            endpoint: "/app/reportes/costo-ventas/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin" },
            cardValue: (data) => data?.total_cost_display ?? "—",
            summaryFields: {
                cost: (data) => data?.total_cost_display ?? "—",
                units: (data) => formatNumber(data?.total_units_display ?? data?.total_units),
                invoices: (data) => formatNumber(data?.ventas_display),
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.factura)}</td>
                    <td>${escapeHtml(row.cliente)}</td>
                    <td>${escapeHtml(row.fecha_display)}</td>
                    <td>${escapeHtml(row.unidades_display)}</td>
                    <td>${escapeHtml(row.costo_total_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron registros para los filtros seleccionados.",
        },
        "inventory-cost": {
            endpoint: "/app/reportes/costo-inventario/",
            supportsRange: false,
            cardValue: (data) => data?.total_cost_display ?? "—",
            summaryFields: {
                value: (data) => data?.total_cost_display ?? "—",
                products: (data) => formatNumber(data?.products_count),
                stock: (data) => formatNumber(data?.total_stock),
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.producto)}</td>
                    <td>${escapeHtml(row.categoria)}</td>
                    <td>${escapeHtml(row.proveedor)}</td>
                    <td>${escapeHtml(row.precio_compra_display)}</td>
                    <td>${formatNumber(row.stock)}</td>
                    <td>${escapeHtml(row.costo_total_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron productos con stock disponible.",
        },
        "sales-period": {
            endpoint: "/app/reportes/ventas-periodo/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin", period: "period" },
            cardValue: (data) => formatNumber(data?.ventas_display),
            summaryFields: {
                count: (data) => formatNumber(data?.ventas_display),
                total: (data) => data?.total_sales_display ?? "—",
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.period_display)}</td>
                    <td>${formatNumber(row.ventas_display ?? row.ventas)}</td>
                    <td>${escapeHtml(row.total_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron ventas para los filtros seleccionados.",
        },
        "profit-period": {
            endpoint: "/app/reportes/ganancias-periodo/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin", period: "period" },
            cardValue: (data) => data?.total_profit_display ?? "—",
            summaryFields: {
                "total-sales": (data) => data?.total_sales_display ?? "—",
                "total-cost": (data) => data?.total_cost_display ?? "—",
                "total-profit": (data) => data?.total_profit_display ?? "—",
                count: (data) => formatNumber(data?.ventas_display),
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.period_display)}</td>
                    <td>${formatNumber(row.ventas_display ?? row.ventas)}</td>
                    <td>${escapeHtml(row.total_sales_display)}</td>
                    <td>${escapeHtml(row.total_cost_display)}</td>
                    <td>${escapeHtml(row.total_profit_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron resultados para los filtros seleccionados.",
        },
        "product-sales": {
            endpoint: "/app/reportes/ventas-producto/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin", search: "q" },
            cardValue: (data) => formatNumber(data?.totals?.productos_display ?? data?.totals?.productos),
            summaryFields: {
                products: (data) => formatNumber(data?.totals?.productos_display ?? data?.totals?.productos),
                quantity: (data) => formatNumber(data?.totals?.cantidad_display ?? data?.totals?.cantidad),
                total: (data) => data?.totals?.venta_display ?? "—",
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.producto)}</td>
                    <td>${escapeHtml(row.marca)}</td>
                    <td>${escapeHtml(row.modelo)}</td>
                    <td>${escapeHtml(row.cantidad_display ?? formatNumber(row.cantidad))}</td>
                    <td>${escapeHtml(row.total_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron resultados para la búsqueda aplicada.",
        },
        "category-analysis": {
            endpoint: "/app/reportes/categorias-analitico/",
            supportsRange: false,
            paramMap: { search: "q" },
            cardValue: (data) => formatNumber(data?.totals?.categorias_display ?? data?.totals?.categorias),
            summaryFields: {
                categories: (data) => formatNumber(data?.totals?.categorias_display ?? data?.totals?.categorias),
                groups: (data) => formatNumber(data?.totals?.grupos_display ?? data?.totals?.grupos),
                products: (data) => formatNumber(data?.totals?.productos_display ?? data?.totals?.productos),
                stock: (data) => formatNumber(data?.totals?.stock_display ?? data?.totals?.stock),
                value: (data) => data?.totals?.valor_display ?? "—",
            },
            rowsExtractor: (data) => (Array.isArray(data?.rows) ? data.rows : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.categoria)}</td>
                    <td>${escapeHtml(row.marca)}</td>
                    <td>${escapeHtml(row.productos_display ?? formatNumber(row.productos))}</td>
                    <td>${escapeHtml(row.stock_display ?? formatNumber(row.stock))}</td>
                    <td>${escapeHtml(row.valor_display)}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron registros que coincidan con la búsqueda.",
        },
        "cash-status": {
            endpoint: "/app/reportes/caja/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin", page_size: "page_size" },
            cardValue: (data) => formatNumber(Array.isArray(data?.sessions) ? data.sessions.length : 0),
            summaryFields: {
                sessions: (data) => formatNumber(Array.isArray(data?.sessions) ? data.sessions.length : 0),
                cash: (data) => formatCurrency(sumBy(data?.sessions, (session) => session?.totals?.total_en_caja)),
                sales: (data) => formatCurrency(sumBy(data?.sessions, (session) => session?.totals?.total)),
            },
            defaultFilters: { page_size: "10" },
            rowsExtractor: (data) => (Array.isArray(data?.sessions) ? data.sessions : []),
            renderRow: (row) => {
                const totals = row?.totals ?? {};
                return `
                    <tr>
                        <td>${escapeHtml(row.apertura_display)}</td>
                        <td>${escapeHtml(row.cierre_display || "—")}</td>
                        <td>${escapeHtml(row.estado_display)}</td>
                        <td>${escapeHtml(totals.total_en_caja_display ?? formatCurrency(totals.total_en_caja))}</td>
                        <td>${escapeHtml(totals.total_display ?? formatCurrency(totals.total))}</td>
                        <td>${escapeHtml(totals.descuento_display ?? formatCurrency(totals.descuento))}</td>
                    </tr>
                `;
            },
            emptyMessage: "No se encontraron sesiones de caja para los filtros aplicados.",
        },
        "credit-installments": {
            endpoint: "/app/reportes/cuotas/",
            supportsRange: true,
            paramMap: { start: "fecha_inicio", end: "fecha_fin", status: "estado" },
            cardValue: (data) => formatNumber(data?.summary?.total_creditos),
            summaryFields: {
                credits: (data) => formatNumber(data?.summary?.total_creditos),
                pending: (data) => data?.summary?.total_pendiente_display ?? formatCurrency(data?.summary?.total_pendiente),
                overdue: (data) => formatNumber(data?.summary?.cuotas_vencidas),
                upcoming: (data) => formatNumber(data?.summary?.proximos_vencimientos),
            },
            rowsExtractor: (data) => (Array.isArray(data?.creditos) ? data.creditos : []),
            renderRow: (row) => `
                <tr>
                    <td>${escapeHtml(row.factura)}</td>
                    <td>${escapeHtml(row.cliente)}</td>
                    <td>${escapeHtml(row.progreso_cuotas ?? "—")}</td>
                    <td>${escapeHtml(row.frecuencia_display ?? "—")}</td>
                    <td>${escapeHtml(row.total_credito_display ?? "—")}</td>
                    <td>${escapeHtml(row.saldo_pendiente_display ?? "—")}</td>
                    <td>${escapeHtml(row.fecha_venta_display ?? "—")}</td>
                    <td>${escapeHtml(row.estado_display ?? "—")}</td>
                </tr>
            `,
            emptyMessage: "No se encontraron créditos para los filtros seleccionados.",
        },
    };

    document.addEventListener("DOMContentLoaded", () => {
        const dashboard = new ReportDashboard(REPORT_CONFIG);
        dashboard.init();
    });

    function escapeHtml(value) {
        if (value === null || value === undefined) {
            return "—";
        }
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function formatNumber(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return "—";
        }
        return NUMBER_FORMAT.format(numeric);
    }

    function formatCurrency(value) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return "—";
        }
        return CURRENCY_FORMAT.format(numeric);
    }

    function sumBy(collection, selector) {
        if (!Array.isArray(collection)) {
            return 0;
        }
        return collection.reduce((acc, item) => {
            const value = Number(selector(item));
            return acc + (Number.isFinite(value) ? value : 0);
        }, 0);
    }

    class ReportDashboard {
        constructor(config) {
            this.config = config;
            this.cards = new Map();
            this.modals = new Map();
            this.activeModal = null;
            this.globalFilters = { start: "", end: "" };
        }

        init() {
            this.cacheElements();
            this.initCards();
            this.initModals();
            this.initRangePicker();
            this.bindEscapeListener();
            this.refreshCards();
        }

        cacheElements() {
            this.cardElements = document.querySelectorAll("[data-report-trigger]");
            this.modalElements = document.querySelectorAll(".report-modal[data-report-modal-type]");
            this.rangeStart = document.querySelector("[data-report-range-start]");
            this.rangeEnd = document.querySelector("[data-report-range-end]");
            this.rangeApplyBtn = document.querySelector("[data-report-range-apply]");
        }

        initCards() {
            this.cardElements.forEach((card) => {
                const type = card.getAttribute("data-report-trigger");
                if (!this.config[type]) {
                    return;
                }
                this.cards.set(type, card);
                card.addEventListener("click", () => this.openModal(type));
            });
        }

        initModals() {
            this.modalElements.forEach((modalEl) => {
                const type = modalEl.getAttribute("data-report-modal-type");
                if (!this.config[type]) {
                    return;
                }
                const modal = new ReportModal(modalEl, type, this);
                this.modals.set(type, modal);
            });
        }

        initRangePicker() {
            if (this.rangeApplyBtn) {
                this.rangeApplyBtn.addEventListener("click", () => {
                    this.globalFilters.start = this.rangeStart?.value || "";
                    this.globalFilters.end = this.rangeEnd?.value || "";
                    this.refreshCards();
                    this.showToast("Rango aplicado correctamente.", "success");
                });
            }
        }

        bindEscapeListener() {
            document.addEventListener("keydown", (event) => {
                if (event.key === "Escape" && this.activeModal) {
                    this.activeModal.close();
                }
            });
        }

        openModal(type) {
            const modal = this.modals.get(type);
            if (!modal) {
                return;
            }
            modal.open();
        }

        setActiveModal(modal) {
            this.activeModal = modal;
        }

        refreshCards() {
            this.cards.forEach((card, type) => {
                const config = this.config[type];
                if (!config) {
                    return;
                }
                this.setCardLoading(card, true);
                this.fetchReport(type, { useGlobalFilters: true })
                    .then((data) => {
                        const value = config.cardValue ? config.cardValue(data) : "—";
                        this.updateCardValue(card, value ?? "—");
                    })
                    .catch((error) => {
                        console.error(error);
                        this.updateCardValue(card, "—");
                        this.showToast(
                            "No fue posible obtener el resumen del reporte.",
                            "error"
                        );
                    })
                    .finally(() => {
                        this.setCardLoading(card, false);
                    });
            });
        }

        setCardLoading(card, isLoading) {
            if (!card) {
                return;
            }
            card.classList.toggle("report-card--loading", isLoading);
            const valueNode = card.querySelector("[data-summary-value]");
            if (valueNode && isLoading) {
                valueNode.textContent = "…";
            }
        }

        updateCardValue(card, value) {
            const target = card.querySelector("[data-summary-value]");
            if (target) {
                target.textContent = value ?? "—";
            }
        }

        fetchReport(type, options = {}) {
            const config = this.config[type];
            if (!config) {
                return Promise.reject(new Error(`Reporte no configurado: ${type}`));
            }

            const params = new URLSearchParams();
            const filters = { ...(config.defaultFilters || {}) };

            if (options.useGlobalFilters && config.supportsRange !== false) {
                if (this.globalFilters.start) {
                    filters.start = this.globalFilters.start;
                }
                if (this.globalFilters.end) {
                    filters.end = this.globalFilters.end;
                }
            }

            if (options.filters) {
                Object.assign(filters, options.filters);
            }

            const map = config.paramMap || {};
            Object.entries(filters).forEach(([key, value]) => {
                if (value === null || value === undefined || value === "") {
                    return;
                }
                const paramName = map[key] || key;
                params.set(paramName, value);
            });

            const url = params.toString()
                ? `${config.endpoint}?${params.toString()}`
                : config.endpoint;

            return fetch(url, {
                method: "GET",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                },
            }).then((response) => {
                if (!response.ok) {
                    throw new Error(`Error HTTP ${response.status}`);
                }
                return response.json();
            });
        }

        showToast(message, type = "info") {
            if (typeof window.showToast === "function") {
                window.showToast(message, type);
            } else {
                console[type === "error" ? "error" : "log"](message);
            }
        }
    }

    class ReportModal {
        constructor(element, type, dashboard) {
            this.element = element;
            this.type = type;
            this.dashboard = dashboard;
            this.config = dashboard.config[type];
            this.isOpen = false;
            this.lastFilters = {};
            this.init();
        }

        init() {
            this.dialog = this.element.querySelector(".report-modal__dialog");
            this.closeButtons = this.element.querySelectorAll("[data-report-close]");
            this.runButton = this.element.querySelector("[data-report-run]");
            this.tableBody = this.element.querySelector("[data-table-body]");
            this.emptyNode = this.element.querySelector("[data-empty]");
            this.summaryNodes = this.element.querySelectorAll("[data-summary]");
            this.filterNodes = this.element.querySelectorAll("[data-filter]");

            this.element.addEventListener("click", (event) => {
                if (event.target === this.element) {
                    this.close();
                }
            });

            this.closeButtons.forEach((button) => {
                button.addEventListener("click", () => this.close());
            });

            if (this.runButton) {
                this.runButton.addEventListener("click", () => this.runReport());
            }
        }

        open() {
            if (this.isOpen) {
                return;
            }
            this.previousActive = document.activeElement;
            this.element.classList.add("is-visible");
            this.element.setAttribute("aria-hidden", "false");
            this.isOpen = true;
            this.dashboard.setActiveModal(this);
            this.syncWithGlobalFilters();
            if (!this.loadedOnce) {
                this.runReport();
            }
        }

        close() {
            if (!this.isOpen) {
                return;
            }
            this.element.classList.remove("is-visible");
            this.element.setAttribute("aria-hidden", "true");
            this.isOpen = false;
            this.dashboard.setActiveModal(null);
            if (this.previousActive && typeof this.previousActive.focus === "function") {
                this.previousActive.focus();
            }
        }

        setLoading(isLoading) {
            this.element.dataset.loading = isLoading ? "true" : "false";
        }

        collectFilters() {
            const data = {};
            this.filterNodes.forEach((node) => {
                const key = node.getAttribute("data-filter");
                if (!key) {
                    return;
                }
                data[key] = node.value ?? "";
            });
            return data;
        }

        syncWithGlobalFilters() {
            if (this.config.supportsRange === false) {
                return;
            }
            this.filterNodes.forEach((node) => {
                const key = node.getAttribute("data-filter");
                if (key === "start" && this.dashboard.globalFilters.start && !node.value) {
                    node.value = this.dashboard.globalFilters.start;
                }
                if (key === "end" && this.dashboard.globalFilters.end && !node.value) {
                    node.value = this.dashboard.globalFilters.end;
                }
            });
        }

        runReport() {
            this.setLoading(true);
            const filters = this.collectFilters();
            this.lastFilters = { ...filters };
            this.dashboard
                .fetchReport(this.type, { filters })
                .then((data) => {
                    this.render(data);
                    this.loadedOnce = true;
                })
                .catch((error) => {
                    console.error(error);
                    this.dashboard.showToast(
                        "Ocurrió un error al generar el reporte.",
                        "error"
                    );
                })
                .finally(() => {
                    this.setLoading(false);
                });
        }

        render(data) {
            this.renderSummary(data);
            this.renderTable(data);
        }

        renderSummary(data) {
            if (!this.summaryNodes || !this.summaryNodes.length) {
                return;
            }
            const summaryConfig = this.config.summaryFields || {};
            this.summaryNodes.forEach((node) => {
                const key = node.getAttribute("data-summary");
                const resolver = summaryConfig[key];
                let value = "—";
                if (typeof resolver === "function") {
                    value = resolver(data) ?? "—";
                } else if (resolver && data && resolver in data) {
                    value = data[resolver] ?? "—";
                }
                node.textContent = value === "" ? "—" : value;
            });
        }

        renderTable(data) {
            if (!this.tableBody) {
                return;
            }
            const rows = this.config.rowsExtractor ? this.config.rowsExtractor(data) : [];
            if (Array.isArray(rows) && rows.length) {
                const html = rows.map((row) => this.config.renderRow(row)).join("");
                this.tableBody.innerHTML = html;
                if (this.emptyNode) {
                    this.emptyNode.hidden = true;
                }
            } else {
                const columnCount = this.getTableColumnCount();
                const message = this.config.emptyMessage || "Sin resultados disponibles.";
                this.tableBody.innerHTML = `
                    <tr>
                        <td colspan="${columnCount}" class="report-empty-state">${escapeHtml(message)}</td>
                    </tr>
                `;
                if (this.emptyNode) {
                    this.emptyNode.hidden = false;
                }
            }
        }

        getTableColumnCount() {
            const table = this.tableBody.closest("table");
            if (!table) {
                return 1;
            }
            const headerCells = table.querySelectorAll("thead th");
            return headerCells.length || 1;
        }
    }
})();
