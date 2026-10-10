/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const STATE_LABELS = {
    draft: "Draft",
    received: "Received",
    ready_dispatch: "Ready to Dispatch",
    dispatched: "Dispatched",
    in_transit: "In Transit",
    arrived: "Arrived",
    ready_collection: "Ready for Collection",
    out_for_delivery: "Out for Delivery",
    delivered: "Delivered",
    cancelled: "Cancelled",
    returned: "Returned",
};

export class ParcelDashboard extends Component {
    static template = "parcel_transport.ParcelDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            kpis: {},
            byDestination: [],
            byStatus: [],
            revenueByDestination: [],
            dailyVolume: [],
        });
        onWillStart(() => this.loadData());
    }

    async loadData() {
        const [stateGroups, destGroups, revenueGroups, unpaidCount, totalCount, dailyRows] = await Promise.all([
            this.orm.formattedReadGroup("parcel.order", [], ["state"], ["__count"]),
            this.orm.formattedReadGroup("parcel.order", [], ["destination"], ["__count"]),
            this.orm.formattedReadGroup(
                "parcel.order", [], ["destination"], ["transport_fee:sum"]
            ),
            this.orm.searchCount("parcel.order", [["payment_status", "=", "unpaid"]]),
            this.orm.searchCount("parcel.order", []),
            this.orm.formattedReadGroup("parcel.order", [], ["create_date:day"], ["__count"]),
        ]);

        const countByState = {};
        for (const g of stateGroups) {
            countByState[g.state] = g.__count || 0;
        }

        const kpis = {
            total: totalCount,
            received: countByState.received || 0,
            in_transit: countByState.in_transit || 0,
            arrived: countByState.arrived || 0,
            ready_collection: countByState.ready_collection || 0,
            delivered: countByState.delivered || 0,
            unpaid: unpaidCount,
            revenue: revenueGroups.reduce((acc, g) => acc + (g["transport_fee:sum"] || 0), 0),
        };

        const byStatus = stateGroups
            .map((g) => ({
                key: g.state,
                label: STATE_LABELS[g.state] || g.state,
                count: g.__count || 0,
            }))
            .sort((a, b) => b.count - a.count);
        const maxStatusCount = Math.max(1, ...byStatus.map((s) => s.count));

        const byDestination = destGroups
            .map((g) => ({
                label: g.destination || "Unknown",
                count: g.__count || 0,
            }))
            .sort((a, b) => b.count - a.count);
        const maxDestCount = Math.max(1, ...byDestination.map((d) => d.count));

        const revenueByDestination = revenueGroups
            .map((g) => ({
                label: g.destination || "Unknown",
                amount: g["transport_fee:sum"] || 0,
            }))
            .sort((a, b) => b.amount - a.amount);
        const maxRevenue = Math.max(1, ...revenueByDestination.map((d) => d.amount));

        const dailyVolume = dailyRows
            .map((g) => ({
                label: g["create_date:day"] ? g["create_date:day"][1] : "",
                count: g.__count || 0,
            }))
            .slice(-14);
        const maxDaily = Math.max(1, ...dailyVolume.map((d) => d.count));

        this.state.kpis = kpis;
        this.state.byStatus = byStatus.map((s) => ({ ...s, pct: (100 * s.count) / maxStatusCount }));
        this.state.byDestination = byDestination.map((d) => ({ ...d, pct: (100 * d.count) / maxDestCount }));
        this.state.revenueByDestination = revenueByDestination.map((d) => ({
            ...d,
            pct: (100 * d.amount) / maxRevenue,
        }));
        this.state.dailyVolume = dailyVolume.map((d) => ({ ...d, pct: (100 * d.count) / maxDaily }));
        this.state.loading = false;
    }

    openParcels(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Parcel Orders",
            res_model: "parcel.order",
            view_mode: "list,kanban,form",
            views: [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ],
            domain: domain || [],
        });
    }
}

registry.category("actions").add("parcel_transport.dashboard", ParcelDashboard);
