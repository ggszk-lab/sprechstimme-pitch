# sprechstimme-pitch

シェーンベルク《月に憑かれたピエロ op.21》No.7 の Sprechstimme（語り歌）を、
録音のピッチ推定から **3 軸（register / range / contour）** で定量分析する研究の
reference implementation．

楽譜指定の音高からの偏差を 3 軸に分解：

- **register（offset）**: 楽譜音高に対する全体的な音高の上下シフト
- **range（compression）**: 楽譜上の音高変動幅に対する圧縮／拡張
- **contour（direction）**: 楽譜の音高輪郭への追従度（score-informed Spearman）

> **Status**: 論文 1 英語版の *Music Performance Research* 投稿（Data and code availability が本リポジトリを参照）に先立って公開．日本語版は日本音楽知覚認知学会 秋季研究発表会 2026（2026-11 中旬予測）で発表予定．

[English README](README.md)

## 5 分で試す（Colab）

<!-- TODO: 公開後に Colab badge を追加 -->
`notebooks/01_quickstart.ipynb` を Colab で開いて Run All．

## ノートブック

- [`notebooks/01_quickstart.ipynb`](notebooks/01_quickstart.ipynb) —
  単一セグメントでの end-to-end パイプライン．3 軸指標までの最短経路．
- [`notebooks/02_paper_reproduction.ipynb`](notebooks/02_paper_reproduction.ipynb) —
  5 録音コーパスでのバッチ処理：per-segment 指標 → per-recording 集約 → 型分類，
  論文 1 主要 3 図（radar / PCA biplot / 型分類フロー）の出力．
  音源がない録音は自動でスキップされるので部分集合でも動く．

## 公開データ（results/）

[`results/`](results/README.md) に論文の派生データを同梱：音符単位の
ピッチ推定値（除外理由付き）・セグメント単位 3 軸指標・型分類サマリ・
感度分析一式（`scripts/sensitivity_e1.py` / `scripts/sensitivity_filter_grid.py`
で再生成可能）・note-by-note の[聴取ログ](results/listening_log.md)．

## ローカルで動かす

```bash
git clone https://github.com/ggszk-lab/sprechstimme-pitch.git
cd sprechstimme-pitch
uv sync                                    # 依存解決
python scripts/fetch_audio.py              # archive.org から音源取得
jupyter lab notebooks/01_quickstart.ipynb
```

## 音源について

本リポジトリは音源ファイルを**含みません**．
`scripts/fetch_audio.py` が archive.org から Stiedry-Wagner 1940 録音を取得します．

- 録音: Schoenberg《月に憑かれたピエロ op.21》Erika Stiedry-Wagner / cond. Schoenberg, 1940（Columbia MM-461）
- 出典: [archive.org/details/SCHONBERGPierrotLunaire-NEWTRANSFER](https://archive.org/details/SCHONBERGPierrotLunaire-NEWTRANSFER)
- アップロード者申告ライセンス: CC BY-NC-SA 3.0

**法的注意**: 米国では Music Modernization Act により本録音は 2041 年まで保護下．
EU・日本では隣接権が 2011 年に失効済み（PD 同等）．
詳細は [LEGAL_NOTICE.md](LEGAL_NOTICE.md) を実行前に必ず参照してください．

## 引用

<!-- TODO: 引用可能な識別子（JSMPC 予稿 / MPR 論文）が確定し次第、引用情報・BibTeX を追加（cite 先はユーザー判断） -->

## ライセンス

- コード: MIT（[LICENSE](LICENSE)）
- メタデータ CSV: CC BY 4.0
- 音源: 同梱せず（[LEGAL_NOTICE.md](LEGAL_NOTICE.md)）

## 関連プロジェクト

- 研究本体（private）: 分析過程・判断ログ・全 22 録音のメタデータ等
- 書籍《演奏分析入門 — 音楽音響の数理と実践》（準備中）: 第 11 章「音高の『揺れ』を記述する」で本リポジトリの notebook を教材として再構成予定
