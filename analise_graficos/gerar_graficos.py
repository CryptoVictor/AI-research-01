import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
from pathlib import Path

# ─── Config ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent
BASE_DIR   = OUTPUT_DIR.parent

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"font.size": 11, "figure.dpi": 150})

STATUS_ORDER  = ["SUCCESS", "WARNED", "BYPASS", "REFUSAL"]
STATUS_COLORS = {
    "SUCCESS": "#4CAF50",
    "WARNED":  "#FFC107",
    "BYPASS":  "#FF5722",
    "REFUSAL": "#2196F3",
}

MODELO_LABELS = {
    "haiku":  "Claude Haiku 4.5",
    "sonnet": "Claude Sonnet 4.6",
}

# ─── Load data ────────────────────────────────────────────────────────────────
haiku  = pd.read_csv(BASE_DIR / "dataset_haiku 4.5.csv")
sonnet = pd.read_csv(BASE_DIR / "dataset_sonnet 4.6.csv")

haiku["MODELO"]  = "Haiku 4.5"
sonnet["MODELO"] = "Sonnet 4.6"
combined = pd.concat([haiku, sonnet], ignore_index=True)

# ─── Helper ───────────────────────────────────────────────────────────────────
def save(fig, name):
    path = OUTPUT_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path.name}")


def status_pct(df):
    counts = df["STATUS_RESPOSTA"].value_counts()
    total  = len(df)
    return {s: counts.get(s, 0) / total * 100 for s in STATUS_ORDER}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Distribuição geral de STATUS por modelo (barras lado a lado)
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(STATUS_ORDER))
w = 0.35

h_pct = status_pct(haiku)
s_pct = status_pct(sonnet)

bars_h = ax.bar(x - w/2, [h_pct[s] for s in STATUS_ORDER], w,
                label="Haiku 4.5",  color=[STATUS_COLORS[s] for s in STATUS_ORDER], alpha=0.75)
bars_s = ax.bar(x + w/2, [s_pct[s] for s in STATUS_ORDER], w,
                label="Sonnet 4.6", color=[STATUS_COLORS[s] for s in STATUS_ORDER], alpha=1.0,
                hatch="//")

for bar in list(bars_h) + list(bars_s):
    h = bar.get_height()
    ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9)

ax.set_xticks(x)
ax.set_xticklabels(STATUS_ORDER)
ax.set_ylabel("% de Respostas")
ax.set_title("Distribuição Geral de STATUS por Modelo")
ax.set_ylim(0, 75)

legend_patches = [
    mpatches.Patch(color="grey", alpha=0.75, label="Haiku 4.5"),
    mpatches.Patch(color="grey", alpha=1.0, hatch="//", label="Sonnet 4.6"),
]
ax.legend(handles=legend_patches)
save(fig, "01_distribuicao_geral_status.png")


# ══════════════════════════════════════════════════════════════════════════════
# 2. STATUS por Categoria (heatmap — porcentagem por modelo)
# ══════════════════════════════════════════════════════════════════════════════
for key, df in [("haiku", haiku), ("sonnet", sonnet)]:
    pivot = (df.groupby(["CATEGORIA", "STATUS_RESPOSTA"])
               .size()
               .unstack(fill_value=0)
               .reindex(columns=STATUS_ORDER, fill_value=0))
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(pivot_pct, annot=True, fmt=".1f", cmap="YlOrRd",
                linewidths=0.5, ax=ax, vmin=0, vmax=100,
                cbar_kws={"label": "%"})
    ax.set_title(f"STATUS por Categoria — {MODELO_LABELS[key]} (%)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    save(fig, f"02_status_por_categoria_{key}.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3. STATUS por Técnica de Ocultação (heatmap)
# ══════════════════════════════════════════════════════════════════════════════
for key, df in [("haiku", haiku), ("sonnet", sonnet)]:
    pivot = (df.groupby(["TECNICA_OCULTACAO", "STATUS_RESPOSTA"])
               .size()
               .unstack(fill_value=0)
               .reindex(columns=STATUS_ORDER, fill_value=0))
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.heatmap(pivot_pct, annot=True, fmt=".1f", cmap="Blues",
                linewidths=0.5, ax=ax, vmin=0, vmax=100,
                cbar_kws={"label": "%"})
    ax.set_title(f"STATUS por Técnica de Ocultação — {MODELO_LABELS[key]} (%)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    plt.xticks(rotation=15)
    save(fig, f"03_status_por_tecnica_{key}.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. STATUS por Tipo de PII (IMPACTO)
# ══════════════════════════════════════════════════════════════════════════════
# Abreviar labels
pii_abbr = {
    "Identificação Pessoal (Nome, CPF, Data de Nascimento, Celular)": "ID Pessoal",
    "Localização (Endereço, CEP, Cidade, Estado)":                    "Localização",
    "Dados Profissionais (Cargo, Empresa, Salário, LinkedIn)":        "Dados Prof.",
    "Segredos de Infraestrutura (API_KEY, DATABASE_URL, JWT_SECRET, ACCESS_TOKEN)": "Segredos Infra",
    "Ativos Web3 (Chave Privada, Frase Semente, Endereço ETH, Mnemônico)":         "Ativos Web3",
}

for key, df in [("haiku", haiku), ("sonnet", sonnet)]:
    df2 = df.copy()
    df2["PII_CURTO"] = df2["IMPACTO (PII)"].map(pii_abbr)
    pivot = (df2.groupby(["PII_CURTO", "STATUS_RESPOSTA"])
                .size()
                .unstack(fill_value=0)
                .reindex(columns=STATUS_ORDER, fill_value=0))
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(pivot_pct, annot=True, fmt=".1f", cmap="Greens",
                linewidths=0.5, ax=ax, vmin=0, vmax=100,
                cbar_kws={"label": "%"})
    ax.set_title(f"STATUS por Tipo de PII — {MODELO_LABELS[key]} (%)")
    ax.set_xlabel("")
    ax.set_ylabel("")
    save(fig, f"04_status_por_pii_{key}.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. EXTRAFILTRADO por modelo (pie charts)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
for ax, (key, df) in zip(axes, [("haiku", haiku), ("sonnet", sonnet)]):
    counts = df["EXTRAFILTRADO"].value_counts()
    ax.pie(counts.values, labels=counts.index,
           autopct="%1.1f%%", colors=["#66BB6A", "#EF5350"],
           startangle=90, textprops={"fontsize": 12})
    ax.set_title(MODELO_LABELS[key])
fig.suptitle("Extra Filtrado (SIM / NÃO) por Modelo", fontsize=13, y=1.02)
save(fig, "05_extrafiltrado_por_modelo.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. STATUS por PROMPT_ID (stacked bar)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
for ax, (key, df) in zip(axes, [("haiku", haiku), ("sonnet", sonnet)]):
    pivot = (df.groupby(["PROMPT_ID", "STATUS_RESPOSTA"])
               .size()
               .unstack(fill_value=0)
               .reindex(columns=STATUS_ORDER, fill_value=0))
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
    pivot_pct.plot(kind="bar", stacked=True, ax=ax,
                   color=[STATUS_COLORS[s] for s in STATUS_ORDER],
                   edgecolor="white", rot=0)
    ax.set_title(MODELO_LABELS[key])
    ax.set_xlabel("Prompt ID")
    ax.set_ylabel("% de Respostas")
    ax.legend(title="Status", bbox_to_anchor=(1, 1))
fig.suptitle("STATUS por Prompt ID", fontsize=13)
plt.tight_layout()
save(fig, "06_status_por_prompt_id.png")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Comparação direta: SUCCESS rate por Categoria (Haiku vs Sonnet)
# ══════════════════════════════════════════════════════════════════════════════
cats = sorted(combined["CATEGORIA"].unique())

def success_rate_by_cat(df):
    return {c: (df[df["CATEGORIA"] == c]["STATUS_RESPOSTA"] == "SUCCESS").mean() * 100 for c in cats}

h_sr = success_rate_by_cat(haiku)
s_sr = success_rate_by_cat(sonnet)

x = np.arange(len(cats))
fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(x - 0.2, [h_sr[c] for c in cats], 0.4, label="Haiku 4.5",  color="#42A5F5", alpha=0.85)
ax.bar(x + 0.2, [s_sr[c] for c in cats], 0.4, label="Sonnet 4.6", color="#AB47BC", alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(cats, rotation=20, ha="right")
ax.set_ylabel("Taxa de SUCCESS (%)")
ax.set_title("Taxa de SUCCESS por Categoria: Haiku 4.5 vs Sonnet 4.6")
ax.legend()
ax.set_ylim(0, 100)
for i, c in enumerate(cats):
    ax.annotate(f"{h_sr[c]:.0f}%", (i - 0.2, h_sr[c] + 1), ha="center", fontsize=8)
    ax.annotate(f"{s_sr[c]:.0f}%", (i + 0.2, s_sr[c] + 1), ha="center", fontsize=8)
save(fig, "07_success_rate_por_categoria.png")


# ══════════════════════════════════════════════════════════════════════════════
# 8. Comparação: BYPASS + SUCCESS (vazamento) por tipo de PII
# ══════════════════════════════════════════════════════════════════════════════
def leak_rate(df):
    return (df["STATUS_RESPOSTA"].isin(["SUCCESS", "BYPASS"])).mean() * 100

pii_types = list(pii_abbr.keys())
pii_short  = list(pii_abbr.values())

h_leak = []
s_leak = []
for p in pii_types:
    h_leak.append(leak_rate(haiku[haiku["IMPACTO (PII)"] == p]))
    s_leak.append(leak_rate(sonnet[sonnet["IMPACTO (PII)"] == p]))

x = np.arange(len(pii_short))
fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(x - 0.2, h_leak, 0.4, label="Haiku 4.5",  color="#EF5350", alpha=0.85)
ax.bar(x + 0.2, s_leak, 0.4, label="Sonnet 4.6", color="#FF8A65", alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(pii_short, rotation=15, ha="right")
ax.set_ylabel("Taxa de Vazamento % (SUCCESS + BYPASS)")
ax.set_title("Taxa de Vazamento de PII por Tipo: Haiku 4.5 vs Sonnet 4.6")
ax.legend()
ax.set_ylim(0, 110)
for i in range(len(pii_short)):
    ax.annotate(f"{h_leak[i]:.0f}%", (i - 0.2, h_leak[i] + 1), ha="center", fontsize=9)
    ax.annotate(f"{s_leak[i]:.0f}%", (i + 0.2, s_leak[i] + 1), ha="center", fontsize=9)
save(fig, "08_taxa_vazamento_por_pii.png")


# ══════════════════════════════════════════════════════════════════════════════
# 9. Técnica de ocultação mais eficaz (menor SUCCESS+BYPASS) por modelo
# ══════════════════════════════════════════════════════════════════════════════
tecnicas = sorted(combined["TECNICA_OCULTACAO"].unique())

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
for ax, (key, df) in zip(axes, [("haiku", haiku), ("sonnet", sonnet)]):
    rates = []
    for t in tecnicas:
        sub = df[df["TECNICA_OCULTACAO"] == t]
        rates.append(leak_rate(sub))

    colors = ["#4CAF50" if r < 40 else "#FFC107" if r < 70 else "#F44336" for r in rates]
    bars = ax.barh(tecnicas, rates, color=colors)
    ax.set_xlabel("Taxa de Vazamento %")
    ax.set_title(MODELO_LABELS[key])
    ax.set_xlim(0, 110)
    for bar, v in zip(bars, rates):
        ax.text(v + 1, bar.get_y() + bar.get_height()/2,
                f"{v:.0f}%", va="center", fontsize=9)

fig.suptitle("Taxa de Vazamento por Técnica de Ocultação", fontsize=13)
plt.tight_layout()
save(fig, "09_vazamento_por_tecnica.png")


# ══════════════════════════════════════════════════════════════════════════════
# 10. Sumário comparativo (tabela estilizada como figura)
# ══════════════════════════════════════════════════════════════════════════════
rows = []
for status in STATUS_ORDER:
    h_cnt = (haiku["STATUS_RESPOSTA"]  == status).sum()
    s_cnt = (sonnet["STATUS_RESPOSTA"] == status).sum()
    rows.append([status,
                 f"{h_cnt} ({h_cnt}%)",
                 f"{s_cnt} ({s_cnt}%)"])

summary = pd.DataFrame(rows, columns=["Status", "Haiku 4.5 (n / %)", "Sonnet 4.6 (n / %)"])

# Recalculate with proper %
rows = []
for status in STATUS_ORDER:
    h_cnt = (haiku["STATUS_RESPOSTA"]  == status).sum()
    s_cnt = (sonnet["STATUS_RESPOSTA"] == status).sum()
    rows.append([status,
                 f"{h_cnt}  ({h_cnt:.0f}%)",
                 f"{s_cnt}  ({s_cnt:.0f}%)"])

summary_data = {
    "Modelo":    ["Haiku 4.5", "Sonnet 4.6"],
    "SUCCESS %": [status_pct(haiku)["SUCCESS"],  status_pct(sonnet)["SUCCESS"]],
    "WARNED %":  [status_pct(haiku)["WARNED"],   status_pct(sonnet)["WARNED"]],
    "BYPASS %":  [status_pct(haiku)["BYPASS"],   status_pct(sonnet)["BYPASS"]],
    "REFUSAL %": [status_pct(haiku)["REFUSAL"],  status_pct(sonnet)["REFUSAL"]],
    "Vazamento % (S+B)": [
        leak_rate(haiku),
        leak_rate(sonnet),
    ],
}
df_sum = pd.DataFrame(summary_data).set_index("Modelo")

fig, ax = plt.subplots(figsize=(10, 2.5))
ax.axis("off")
tbl = ax.table(
    cellText=df_sum.round(1).values,
    colLabels=df_sum.columns,
    rowLabels=df_sum.index,
    cellLoc="center", loc="center",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(11)
tbl.scale(1.4, 2.2)

# Color header
for (row, col), cell in tbl.get_celld().items():
    if row == 0:
        cell.set_facecolor("#37474F")
        cell.set_text_props(color="white", fontweight="bold")
    elif col == -1:
        cell.set_facecolor("#ECEFF1")
        cell.set_text_props(fontweight="bold")

ax.set_title("Sumário Comparativo — Haiku 4.5 vs Sonnet 4.6", fontsize=13, pad=20)
save(fig, "10_sumario_comparativo.png")


print("\nTodos os gráficos gerados com sucesso!")
