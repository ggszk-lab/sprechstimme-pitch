"""Visualizations: radar chart, PCA biplot, type classification.

Provides plotting functions for the three-axis decomposition analysis.
"""

from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .metrics import (
    THRESHOLD_CONTOUR_STD,
    THRESHOLD_OFFSET_ABS_CENT,
    classify_performance,
)

__all__ = [
    "RECORDINGS",
    "COLOR_MAP",
    "MARKER_MAP",
    "RECORDING_LABELS",
    "TYPE_COLOR",
    "TYPE_LABEL",
    "four_axes_normalize",
    "plot_radar_chart",
    "plot_pca_biplot",
    "plot_type_classification_flow",
]


# Recording identification and styling.
# These constants are tuned for the 5-recording paper-1 corpus; expand
# them when extending the analysis to additional recordings.
RECORDINGS = ['ath-1973', 'hul-2012', 'bou-1961', 'bou-1977', 'her-1991']

COLOR_MAP = {
    'ath-1973': 'C0',
    'hul-2012': 'C1',
    'bou-1961': 'C3',
    'bou-1977': 'C2',
    'her-1991': 'C4',
}

MARKER_MAP = {
    'ath-1973': 'o',
    'hul-2012': 's',
    'bou-1961': '^',
    'bou-1977': 'v',
    'her-1991': 'D',
}

RECORDING_LABELS = {
    'ath-1973': 'Atherton (1973)',
    'hul-2012': 'Hulburt (2012)',
    'bou-1961': 'Boulez (1961)',
    'bou-1977': 'Boulez (1977)',
    'her-1991': 'Heringer (1991)',
}

TYPE_COLOR = {
    'score-faithful': '#4C9F70',
    'directed-recitation': '#C44E52',
    'dynamic': '#8172B2',
}

TYPE_LABEL = {
    'score-faithful': 'Score-Faithful',
    'directed-recitation': 'Directed Recitation',
    'dynamic': 'Dynamic',
}


def four_axes_normalize(
    register_offset_cent: float,
    range_compression: float,
    contour_correlation: float,
    contour_std: float,
) -> dict[str, float]:
    """
    Compute normalized 4-axis values for radar chart.

    Axes:
    - abs_offset: |register_offset| / 1000 (transpose deviation)
    - range_dev: |1 - range_compression| (range deviation)
    - contour_dev: 1 - contour_correlation (contour deviation)
    - contour_std: contour standard deviation (dynamic quality)

    Args:
        register_offset_cent: median pitch offset in cents
        range_compression: observed/score pitch span ratio
        contour_correlation: Spearman r of pitch contour
        contour_std: std of contour_correlation across segments

    Returns:
        dict with normalized axis values.
    """
    return {
        'abs_offset': abs(register_offset_cent) / 1000.0,
        'range_dev': abs(1.0 - range_compression),
        'contour_dev': 1.0 - (contour_correlation if not np.isnan(contour_correlation) else 0),
        'contour_std': contour_std if not np.isnan(contour_std) else 0,
    }


def plot_radar_chart(
    recordings_data: dict[str, dict[str, float]],
    figsize: tuple[int, int] = (14, 3),
) -> tuple[plt.Figure, np.ndarray]:
    """
    Plot radar charts for multiple recordings.

    Args:
        recordings_data: dict mapping rec_id → dict of normalized axes.
            Each inner dict should have keys: abs_offset, range_dev, contour_dev, contour_std.
        figsize: figure size (width, height)

    Returns:
        (Figure, axes array)
    """
    axis_keys = ['abs_offset', 'range_dev', 'contour_dev', 'contour_std']
    axis_labels = [
        '|offset|/1000\n(transpose)',
        '|1-range|\n(range dev.)',
        '1-contour\n(contour dev.)',
        'contour_std\n(dynamic)',
    ]

    angles = np.linspace(0, 2 * np.pi, len(axis_keys), endpoint=False).tolist()
    angles += angles[:1]  # Close the polygon

    # Compute axis limits from data
    all_values = []
    for rec_data in recordings_data.values():
        all_values.extend([rec_data.get(k, 0) for k in axis_keys])
    axis_max = max(all_values) * 1.1 if all_values else 1.0

    n_recordings = len(recordings_data)
    fig, axes = plt.subplots(
        1, n_recordings, figsize=figsize, subplot_kw=dict(projection='polar')
    )
    if n_recordings == 1:
        axes = np.array([axes])

    for idx, (rec_id, ax) in enumerate(zip(recordings_data.keys(), axes)):
        values = [recordings_data[rec_id].get(k, 0) for k in axis_keys]
        values += values[:1]

        ax.plot(angles, values, 'o-', linewidth=2, label=rec_id)
        ax.fill(angles, values, alpha=0.25)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(axis_labels, size=9)
        ax.set_ylim(0, axis_max)
        ax.set_title(RECORDING_LABELS.get(rec_id, rec_id), size=11, pad=20)
        ax.grid(True)

    plt.tight_layout()
    return fig, axes


def plot_pca_biplot(
    recordings_data: dict[str, dict[str, float]],
    figsize: tuple[int, int] = (8, 8),
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot PCA biplot of normalized four-axis metrics.

    Args:
        recordings_data: dict mapping rec_id → normalized axes dict
        figsize: figure size

    Returns:
        (Figure, Axes)
    """
    axis_keys = ['abs_offset', 'range_dev', 'contour_dev', 'contour_std']
    rec_ids = list(recordings_data.keys())

    # Prepare data matrix (n_recordings × n_features)
    X = np.array([[recordings_data[rid].get(k, 0) for k in axis_keys] for rid in rec_ids])

    # Standardize and project
    scaler = StandardScaler()
    X_std = scaler.fit_transform(X)

    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_std)

    fig, ax = plt.subplots(figsize=figsize)

    # Plot recordings
    for i, rec_id in enumerate(rec_ids):
        ax.scatter(
            X_pca[i, 0],
            X_pca[i, 1],
            s=200,
            c=COLOR_MAP.get(rec_id, 'C0'),
            marker=MARKER_MAP.get(rec_id, 'o'),
            label=RECORDING_LABELS.get(rec_id, rec_id),
            edgecolors='black',
            linewidth=1.5,
            zorder=3,
        )

    # Plot loading vectors
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    arrow_scale = 0.85 * float(np.abs(X_pca).max())

    for i, key in enumerate(axis_keys):
        ax.arrow(
            0,
            0,
            loadings[i, 0] * arrow_scale,
            loadings[i, 1] * arrow_scale,
            head_width=0.15,
            head_length=0.15,
            fc='gray',
            ec='gray',
            alpha=0.6,
        )
        ax.text(
            loadings[i, 0] * arrow_scale * 1.15,
            loadings[i, 1] * arrow_scale * 1.15,
            key,
            fontsize=10,
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
        )

    ax.axhline(y=0, color='k', linewidth=0.5, linestyle='--', alpha=0.3)
    ax.axvline(x=0, color='k', linewidth=0.5, linestyle='--', alpha=0.3)

    ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})', fontsize=12)
    ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})', fontsize=12)
    ax.set_title('PCA Biplot: Three-Axis Decomposition', fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig, ax


def plot_type_classification_flow(
    recordings_data: dict[str, tuple[float, float]],
    figsize: tuple[int, int] = (12, 6),
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot decision tree-style classification flow.

    Args:
        recordings_data: dict mapping rec_id → (register_offset, contour_std)
        figsize: figure size

    Returns:
        (Figure, Axes)
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Decision nodes (relative positions)
    nodes = {
        'start': (0.5, 0.9),
        'contour_decision': (0.5, 0.7),
        'dynamic': (0.3, 0.45),
        'offset_decision': (0.7, 0.5),
        'directed': (0.85, 0.25),
        'faithful': (0.55, 0.25),
    }

    # Draw decision nodes
    def draw_box(ax, pos, label, color='lightblue', width=0.12, height=0.08):
        rect = FancyBboxPatch(
            (pos[0] - width / 2, pos[1] - height / 2),
            width,
            height,
            boxstyle='round,pad=0.01',
            edgecolor='black',
            facecolor=color,
            linewidth=2,
        )
        ax.add_patch(rect)
        ax.text(pos[0], pos[1], label, ha='center', va='center', fontsize=10, fontweight='bold')

    draw_box(ax, nodes['start'], 'Start', 'lightgray')
    contour_label = f'contour_std\n> {THRESHOLD_CONTOUR_STD}?'
    draw_box(ax, nodes['contour_decision'], contour_label, 'lightyellow')
    draw_box(ax, nodes['dynamic'], 'Dynamic', TYPE_COLOR['dynamic'])
    offset_label = f'|offset|\n> {int(THRESHOLD_OFFSET_ABS_CENT)}c?'
    draw_box(ax, nodes['offset_decision'], offset_label, 'lightyellow')
    draw_box(ax, nodes['directed'], 'Directed\nRecitation', TYPE_COLOR['directed-recitation'])
    draw_box(ax, nodes['faithful'], 'Score-\nFaithful', TYPE_COLOR['score-faithful'])

    # Draw arrows
    def draw_arrow(ax, start, end, label=''):
        ax.annotate(
            '',
            xy=end,
            xytext=start,
            arrowprops=dict(arrowstyle='->', lw=2, color='black'),
        )
        if label:
            mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            ax.text(mid[0], mid[1] + 0.02, label, fontsize=9, ha='center', style='italic')

    draw_arrow(ax, nodes['start'], nodes['contour_decision'])
    draw_arrow(ax, nodes['contour_decision'], nodes['dynamic'], 'YES')
    draw_arrow(ax, nodes['contour_decision'], nodes['offset_decision'], 'NO')
    draw_arrow(ax, nodes['offset_decision'], nodes['directed'], 'YES')
    draw_arrow(ax, nodes['offset_decision'], nodes['faithful'], 'NO')

    # Plot recordings on the result nodes
    for rec_id, (offset, c_std) in recordings_data.items():
        rec_type = classify_performance(offset, c_std)
        node_pos = nodes[
            'dynamic' if rec_type == 'dynamic'
            else 'directed' if rec_type == 'directed-recitation'
            else 'faithful'
        ]
        ax.scatter(
            node_pos[0],
            node_pos[1] - 0.12,
            s=100,
            c=COLOR_MAP.get(rec_id, 'C0'),
            marker=MARKER_MAP.get(rec_id, 'o'),
            edgecolors='black',
            linewidth=1.5,
            zorder=5,
        )

    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.0)
    ax.axis('off')
    ax.set_title('Performance Type Classification', fontsize=13, fontweight='bold', pad=20)

    plt.tight_layout()
    return fig, ax
