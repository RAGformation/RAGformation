import asyncio
import nest_asyncio
from workflows.concierge_workflow import ConciergeWorkflow


async def main():
    c = ConciergeWorkflow(timeout=1200, verbose=True)
    result = await c.run()
    print(result)


if __name__ == "__main__":
    try:
        if not asyncio.get_event_loop().is_running():
            asyncio.run(main())
        else:
            try:
                pass  # For Jupyter, uncomment: await main()
            except Exception as e:
                print(e)
    except RuntimeError:
        nest_asyncio.apply()
        asyncio.run(main())

# Uncomment to generate workflow diagram
# draw_all_possible_flows(ConciergeWorkflow, filename="concierge_flows.html")
