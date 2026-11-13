import sys
from decimal import Decimal
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings


def generate_cost_projection():
    settings = get_settings()

    usd_inr = Decimal(str(settings.USD_INR_RATE))

    # Token Pricing per 1M tokens in USD
    p_in_router = Decimal(str(settings.PRICE_PER_1M_INPUT_TOKENS_USD_ROUTER))
    p_out_router = Decimal(str(settings.PRICE_PER_1M_OUTPUT_TOKENS_USD_ROUTER))
    p_in_gen = Decimal(str(settings.PRICE_PER_1M_INPUT_TOKENS_USD_GENERATOR))
    p_out_gen = Decimal(str(settings.PRICE_PER_1M_OUTPUT_TOKENS_USD_GENERATOR))

    # Average Token Footprint per Turn
    router_in_tokens = 350
    router_out_tokens = 40
    gen_in_tokens = 950  # includes system prompt, 6 history turns, user message, retrieved chunks/products
    gen_out_tokens = 120

    # Per Turn Costs (USD)
    router_turn_cost_usd = (
        Decimal(router_in_tokens) * p_in_router + Decimal(router_out_tokens) * p_out_router
    ) / Decimal(1_000_000)
    gen_turn_cost_usd = (Decimal(gen_in_tokens) * p_in_gen + Decimal(gen_out_tokens) * p_out_gen) / Decimal(
        1_000_000
    )
    total_turn_cost_usd = router_turn_cost_usd + gen_turn_cost_usd

    # Per Turn Costs (INR)
    router_turn_cost_inr = router_turn_cost_usd * usd_inr
    gen_turn_cost_inr = gen_turn_cost_usd * usd_inr
    total_turn_cost_inr = total_turn_cost_usd * usd_inr

    # Volume Scenarios
    # 1. Normal Month: 50,000 sessions * 3 turns/session = 150,000 turns
    normal_sessions = 50_000
    normal_turns = normal_sessions * 3
    normal_cost_usd = total_turn_cost_usd * normal_turns
    normal_cost_inr = normal_cost_usd * usd_inr

    # 2. Festival Peak Month (5x traffic spike): 250,000 sessions = 750,000 turns
    festival_sessions = 250_000
    festival_turns = festival_sessions * 3
    festival_cost_usd = total_turn_cost_usd * festival_turns
    festival_cost_inr = festival_cost_usd * usd_inr

    print("=" * 75)
    print("GROQ LLM INFRASTRUCTURE COST PROJECTION REPORT")
    print("=" * 75)
    print(f"Currency Conversion Rate:   1 USD = ₹{usd_inr:.2f}")
    print(f"Router Model:               {settings.ROUTER_MODEL} (${p_in_router}/$ {p_out_router} per 1M)")
    print(f"Generator Model:            {settings.GENERATOR_MODEL} (${p_in_gen}/$ {p_out_gen} per 1M)")
    print("-" * 75)
    print("TOKEN & COST BREAKDOWN PER TURN:")
    print(
        f"  • Router Turn ({router_in_tokens} in / {router_out_tokens} out):       ${router_turn_cost_usd:.6f}  (₹{router_turn_cost_inr:.4f})"
    )
    print(
        f"  • Generator Turn ({gen_in_tokens} in / {gen_out_tokens} out):    ${gen_turn_cost_usd:.6f}  (₹{gen_turn_cost_inr:.4f})"
    )
    print(
        f"  • Total Cost per Customer Turn:            ${total_turn_cost_usd:.6f}  (₹{total_turn_cost_inr:.4f})"
    )
    print("-" * 75)
    print("MONTHLY PROJECTIONS:")
    print(f"  [Standard Monthly Volume] ({normal_sessions:,} sessions / {normal_turns:,} turns):")
    print(f"     Total USD: ${normal_cost_usd:,.2f}")
    print(f"     Total INR: ₹{normal_cost_inr:,.2f}")
    print()
    print(
        f"  [Festival Sale Spike (5x Traffic)] ({festival_sessions:,} sessions / {festival_turns:,} turns):"
    )
    print(f"     Total USD: ${festival_cost_usd:,.2f}")
    print(f"     Total INR: ₹{festival_cost_inr:,.2f}")
    print("=" * 75)

    return {
        "turn_cost_inr": float(total_turn_cost_inr),
        "normal_cost_inr": float(normal_cost_inr),
        "festival_cost_inr": float(festival_cost_inr),
    }


if __name__ == "__main__":
    generate_cost_projection()
