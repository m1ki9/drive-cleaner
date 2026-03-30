from __future__ import annotations

from matplotlib.figure import Figure


def create_top_folders_figure(rows: list[tuple[str, int]], chart_type: str = "bar") -> Figure:
    labels = [item[0] for item in rows]
    sizes = [item[1] for item in rows]

    figure = Figure(figsize=(7, 4.5), dpi=100)
    axis = figure.add_subplot(111)

    if not labels:
        axis.text(0.5, 0.5, "No scan data", ha="center", va="center")
        axis.set_axis_off()
        return figure

    if chart_type == "pie":
        short_labels = [label[-35:] for label in labels[:8]]
        axis.pie(sizes[:8], labels=short_labels, autopct="%1.1f%%", startangle=90)
        axis.set_title("Top Folder Share")
    else:
        show_labels = [label[-45:] for label in labels[:12]]
        show_sizes_gb = [size / (1024**3) for size in sizes[:12]]
        axis.barh(show_labels, show_sizes_gb)
        axis.invert_yaxis()
        axis.set_xlabel("Size (GB)")
        axis.set_title("Top Folders by Size")

    figure.tight_layout()
    return figure
