# Anime Studio Positioning Map

アニメスタジオのポジショニングマップ（インタラクティブ）。

Plotly.js を使用したインタラクティブな散布図で、国内外のアニメスタジオを複数の軸で可視化します。

## 公開URL

- **マップ**: https://murasaqi.github.io/anime-studio-positioning-map/
- **ドキュメント一覧**: https://murasaqi.github.io/anime-studio-positioning-map/docs/

## ディレクトリ構成

```
anime-studio-positioning-map/
├── _config.yml              # Jekyll設定（Caymanテーマ）
├── _layouts/
│   └── default.html         # ドキュメント用レイアウト（noindex付き）
├── index.html               # ポジショニングマップ本体
├── robots.txt               # 検索エンジン除外設定
├── create_plotly_map.py     # マップ生成スクリプト
├── positioning_map.pptx     # PowerPoint版マップ
├── data/
│   ├── studios_merged.yaml  # 統合スタジオデータ
│   ├── studios_domestic.yaml    # 国内スタジオデータ
│   └── studios_international.yaml # 海外スタジオデータ
├── docs/                    # ★ ドキュメントはここに追加
│   ├── index.md             # ドキュメント一覧（自動生成）
│   ├── branding-research-report.md
│   ├── business-strategy-report.md
│   └── research-instructions.md
└── workspace/               # ビルドツール
    ├── create_pptx.cjs
    └── slides/
```

## ドキュメントの追加方法

`docs/` にMarkdownファイルを置くだけで、ドキュメント一覧に自動表示されます。

### 手順

1. `docs/` に `.md` ファイルを作成（**英語ケバブケース**のファイル名）
2. 先頭にフロントマターを記載:

```yaml
---
layout: default
title: "ドキュメントタイトル"     # 必須: 一覧・ナビに表示
description: "簡潔な説明"         # 必須: 一覧ページの概要欄
order: 1                          # 任意: 表示順（小さい順、未指定は末尾）
---
```

3. コミット & プッシュ:

```bash
git add docs/new-doc.md
git commit -m "docs: 新しいドキュメントを追加"
git push origin main
```

4. 一覧ページに自動的に追加される（手動でリンクを書く必要なし）

## データソース

全データは Wikipedia、企業公式サイト、ニュース記事、IR資料等の公開情報から収集しています。
