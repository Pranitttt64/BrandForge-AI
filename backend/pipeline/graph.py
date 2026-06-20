"""
LangGraph pipeline graph for BrandForge AI.
Defines the 10-node pipeline with parallel fan-out at the creative stage.
"""

from langgraph.graph import StateGraph, END
from langgraph.constants import Send

from pipeline.state import BrandForgeState


def create_pipeline_graph():
    # Import nodes here to avoid circular imports at module level
    from pipeline.nodes.scraper import scraper_node_async
    from pipeline.nodes.brand_extractor import brand_extractor_node
    from pipeline.nodes.rag_ingestor import rag_ingestor_node
    from pipeline.nodes.copywriter import copywriter_node
    from pipeline.nodes.layout_agent import layout_node
    from pipeline.nodes.email_agent import email_node
    from pipeline.nodes.ad_agent import ad_node
    from pipeline.nodes.critic import critic_node
    from pipeline.nodes.asset_generator import asset_generator_node
    from pipeline.nodes.zip_packager import zip_packager_node

    def route_to_parallel(state: BrandForgeState):
        """Fan-out router: sends state to 4 creative agents in parallel."""
        return [
            Send("copywriter",    state),
            Send("layout_agent",  state),
            Send("email_agent",   state),
            Send("ad_agent",      state),
        ]

    builder = StateGraph(BrandForgeState)

    # Register nodes
    builder.add_node("scraper",         scraper_node_async)
    builder.add_node("brand_extractor", brand_extractor_node)
    builder.add_node("rag_ingestor",    rag_ingestor_node)
    builder.add_node("copywriter",      copywriter_node)
    builder.add_node("layout_agent",    layout_node)
    builder.add_node("email_agent",     email_node)
    builder.add_node("ad_agent",        ad_node)
    builder.add_node("critic",          critic_node)
    builder.add_node("asset_generator", asset_generator_node)
    builder.add_node("zip_packager",    zip_packager_node)

    # Sequential edges
    builder.set_entry_point("scraper")
    builder.add_edge("scraper",         "brand_extractor")
    builder.add_edge("brand_extractor", "rag_ingestor")

    # Parallel fan-out from rag_ingestor
    builder.add_conditional_edges(
        "rag_ingestor",
        route_to_parallel,
        ["copywriter", "layout_agent", "email_agent", "ad_agent"],
    )

    # Fan-in: all 4 creative agents → critic
    builder.add_edge("copywriter",    "critic")
    builder.add_edge("layout_agent",  "critic")
    builder.add_edge("email_agent",   "critic")
    builder.add_edge("ad_agent",      "critic")

    # Final sequential stages
    builder.add_edge("critic",          "asset_generator")
    builder.add_edge("asset_generator", "zip_packager")
    builder.add_edge("zip_packager",    END)

    return builder.compile()


# Compiled graph — imported by job_manager
graph = create_pipeline_graph()