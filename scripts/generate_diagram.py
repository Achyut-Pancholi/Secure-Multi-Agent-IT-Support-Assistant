import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_diagram():
    # Setup high-resolution figure with modern styling
    fig, ax = plt.subplots(figsize=(16, 12), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # Color palette
    COLOR_AGENT = '#2563EB'      # Blue
    COLOR_GUARD = '#DC2626'      # Red/Burgundy
    COLOR_TOOL = '#059669'       # Emerald Green
    COLOR_STORAGE = '#7C3AED'    # Purple
    COLOR_IO = '#0F172A'         # Slate dark
    COLOR_OBS = '#D97706'        # Amber

    def draw_box(x, y, w, h, title, subtitle, color, icon=""):
        # Shadow
        shadow = patches.FancyBboxPatch(
            (x + 0.05, y - 0.05), w, h,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            facecolor="#E2E8F0", edgecolor="none", zorder=1
        )
        ax.add_patch(shadow)

        # Main Box
        box = patches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            facecolor="white", edgecolor=color, linewidth=2.0, zorder=2
        )
        ax.add_patch(box)

        # Header bar
        header_h = h * 0.38
        header = patches.FancyBboxPatch(
            (x, y + h - header_h), w, header_h,
            boxstyle="round,pad=0.08,rounding_size=0.18",
            facecolor=color, edgecolor=color, linewidth=0, zorder=3
        )
        ax.add_patch(header)

        # Title text
        ax.text(
            x + w / 2, y + h - (header_h / 2), title,
            color='white', fontsize=11, fontweight='bold',
            ha='center', va='center', zorder=4
        )

        # Subtitle text
        ax.text(
            x + w / 2, y + (h - header_h) / 2, subtitle,
            color='#334155', fontsize=9, ha='center', va='center',
            style='italic', zorder=4
        )

    def draw_arrow(x1, y1, x2, y2, label="", rad=0.0, color="#475569"):
        connectionstyle = f"arc3,rad={rad}" if rad != 0.0 else "arc3"
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=2.0,
                mutation_scale=16,
                connectionstyle=connectionstyle
            ),
            zorder=5
        )
        if label:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2 + 0.15
            ax.text(
                mid_x, mid_y, label,
                fontsize=8.5, fontweight='bold', color=color,
                ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", fc="#F8FAFC", ec="none", alpha=0.9),
                zorder=6
            )

    # Title & Subtitle Banner
    ax.text(8.0, 11.5, "Secure Multi-Agent IT Support Assistant", fontsize=20, fontweight='bold', ha='center', color='#0F172A')
    ax.text(8.0, 11.15, "AI Workflow & Agentic Orchestration Architecture (LangGraph + Groq OpenAI OSS Models)", fontsize=11.5, ha='center', color='#64748B')

    # Column Coordinates
    COL_LEFT = 2.8
    COL_CENTER = 8.0
    COL_RIGHT = 13.2

    # Center Pipeline Nodes
    # 1. User
    draw_box(COL_CENTER - 1.5, 9.9, 3.0, 0.9, "User Input", "Chat Request / IT Ticket Query", COLOR_IO)

    # 2. Input Guardrail
    draw_box(COL_CENTER - 1.7, 8.5, 3.4, 0.9, "Input Guardrail", "Sanitization & Prompt Injection Check", COLOR_GUARD)
    draw_arrow(COL_CENTER, 9.9, COL_CENTER, 9.4)

    # 3. Triage Agent
    draw_box(COL_CENTER - 1.8, 7.0, 3.6, 1.0, "Triage Agent", "Groq / openai/gpt-oss-120b\nClassify Category & Routing", COLOR_AGENT)
    draw_arrow(COL_CENTER, 8.5, COL_CENTER, 8.0)

    # Left Branch: Knowledge Path
    # 4a. Knowledge Agent
    draw_box(COL_LEFT - 1.7, 5.2, 3.4, 1.0, "Knowledge Agent", "Reasoning & Guidance Formulation", COLOR_AGENT)
    draw_arrow(COL_CENTER - 1.8, 7.4, COL_LEFT, 6.2, label="Route: KNOWLEDGE", rad=0.15, color='#2563EB')

    # 5a. Knowledge Tool
    draw_box(COL_LEFT - 1.7, 3.7, 3.4, 0.9, "Knowledge Tool", "search_knowledge_base()", COLOR_TOOL)
    draw_arrow(COL_LEFT, 5.2, COL_LEFT, 4.6)

    # 6a. Chroma Vector Store
    draw_box(COL_LEFT - 1.7, 2.3, 3.4, 0.9, "Chroma Vector DB", "HuggingFace MiniLM Embeddings (Local)", COLOR_STORAGE)
    draw_arrow(COL_LEFT, 3.7, COL_LEFT, 3.2)

    # Right Branch: Action Path
    # 4b. Action Agent
    draw_box(COL_RIGHT - 1.7, 5.2, 3.4, 1.0, "Action Agent", "Tool Invocation & State Inspection", COLOR_AGENT)
    draw_arrow(COL_CENTER + 1.8, 7.4, COL_RIGHT, 6.2, label="Route: ACTION", rad=-0.15, color='#2563EB')

    # 5b. Tool Guardrail
    draw_box(COL_RIGHT - 1.7, 3.7, 3.4, 0.9, "Tool Guardrail", "Policy Authorization & Access Rules", COLOR_GUARD)
    draw_arrow(COL_RIGHT, 5.2, COL_RIGHT, 4.6)

    # 6b. Internal Mock API & Tools
    draw_box(COL_RIGHT - 1.8, 2.3, 3.6, 0.9, "Mock Internal IT APIs", "access, service status, create ticket", COLOR_TOOL)
    draw_arrow(COL_RIGHT, 3.7, COL_RIGHT, 3.2, label="Authorized Calls")

    # Converge at Response Agent
    draw_box(COL_CENTER - 1.8, 3.3, 3.6, 1.0, "Response Agent", "Groq / openai/gpt-oss-120b\nContext Synthesis & Formulation", COLOR_AGENT)
    draw_arrow(COL_LEFT + 1.7, 4.1, COL_CENTER - 1.8, 3.8, rad=-0.12)
    draw_arrow(COL_RIGHT - 1.7, 4.1, COL_CENTER + 1.8, 3.8, rad=0.12)
    draw_arrow(COL_CENTER, 7.0, COL_CENTER, 4.3, label="Direct / Fallback", color='#94A3B8')

    # Output Guardrail
    draw_box(COL_CENTER - 1.7, 1.8, 3.4, 0.9, "Output Guardrail", "Mask Secrets & Block IP Leaks", COLOR_GUARD)
    draw_arrow(COL_CENTER, 3.3, COL_CENTER, 2.7)

    # Final User Response
    draw_box(COL_CENTER - 1.5, 0.4, 3.0, 0.9, "Final Response", "Streamed (SSE) / REST Output", COLOR_IO)
    draw_arrow(COL_CENTER, 1.8, COL_CENTER, 1.3)

    # Lateral Memory & Observability Badges
    # Long-term memory badge (top left)
    draw_box(0.4, 9.0, 3.2, 1.0, "Long-Term Memory", "SQLite DB (User Profile & Device Info)", COLOR_STORAGE)
    draw_arrow(3.6, 9.5, COL_CENTER - 1.7, 9.0, label="Enrich Context", rad=-0.1, color=COLOR_STORAGE)

    # Observability badge (top right)
    draw_box(12.4, 9.0, 3.2, 1.0, "Observability Stack", "Local Langfuse (Traces) + Python Logs", COLOR_OBS)
    draw_arrow(12.4, 9.5, COL_CENTER + 1.7, 9.0, label="Trace & Monitor", rad=0.1, color=COLOR_OBS)

    # Output directory
    output_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ai_workflow.png")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Diagram successfully generated at: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    draw_diagram()

