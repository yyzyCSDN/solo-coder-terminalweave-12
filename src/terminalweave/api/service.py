from __future__ import annotations
from datetime import datetime
from terminalweave.marine.tide import TideCurve, TideSample, UnderKeelRequirement
from terminalweave.billing.demurrage import BusinessCalendar, DemurrageTariff, TariffBand, DemurrageCalculator
from terminalweave.core.money import Money
from decimal import Decimal

class TerminalService:

    def health(self) -> dict[str, object]:
        return {'status': 'ok', 'service': 'terminalweave'}

    def tide_clearance(self, payload: dict[str, object]) -> dict[str, object]:
        samples = [TideSample(datetime.fromisoformat(x['at'].replace('Z', '+00:00')), float(x['height_m'])) for x in payload['samples']]
        curve = TideCurve(samples)
        req = UnderKeelRequirement(float(payload['chart_depth_m']), float(payload['draft_m']), float(payload['minimum_clearance_m']), float(payload.get('squat_allowance_m', 0)), float(payload.get('wave_allowance_m', 0)))
        at = datetime.fromisoformat(str(payload['at']).replace('Z', '+00:00'))
        return {'safe': curve.is_safe(at, req), 'clearance_m': curve.clearance_m(at, req)}

    def demurrage_quote(self, payload: dict[str, object]) -> dict[str, object]:
        currency = str(payload.get('currency', 'USD'))
        rate = Money(Decimal(str(payload['daily_rate'])), currency)
        tariff = DemurrageTariff(int(payload.get('free_days', 0)), (TariffBand(1, None, rate),))
        calc = DemurrageCalculator(BusinessCalendar(), tariff)
        start = datetime.fromisoformat(str(payload['discharge_at']).replace('Z', '+00:00'))
        end = datetime.fromisoformat(str(payload['gate_out_at']).replace('Z', '+00:00'))
        total = calc.total(start, end)
        return {'amount': str(total.amount), 'currency': total.currency}
