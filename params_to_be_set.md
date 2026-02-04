# UI上で設定できるべき変数
## 凡例
- 該当するalproj関数名
    - 変数: デフォルト値: 説明（指定されてない場合はあなたが考えて日本語で書く）

## 対象の関数
- get_colored_surface
    - distance: 3000: レンダリングする最大距離。撮影点から最も遠い写真中の点までの距離より大きい値を入れる。
- sim_image
    - min_distance: 100: これより近い場所はシミュレーション画像でレンダリングされない。近距離での誤マッチングを避けるのに有用
- image_match
    - method: superpoint-lightglue: マッチング手法。akaze/siftは高速で軽量だが特に近距離での性能が低い。superpoint-lightglueは軽量で比較的高性能。ufm、minima-romaは重くRAMを多く（16GB以上推奨）必要とするが、極めて高性能。
    - outlier_filter (fundamental固定。二段階推定を行う場合の二段階目ではessential固定。選択不要。)
    - resize: ufm, minima-romaでは800。sift, akaze, superpoint-lightglueではnone。: 画像のリサイズ。ufm, minima-romaでは800px以下へのリサイズを推奨。
    - threshold: 30
    - spatial-thin-grid: 50
    - spatial_thin_selection (centerで固定。選択不要。)
- filter_gcp_distance
    - min_distance: 100
cma_optimizer.set_target: カメラ位置、カメラ向き、画角、歪み、からトグルで選べるようにする。デフォルトでは全て。: 推定するカメラパラメータ
- cma_optimizer.optimize
    - generation = 300, sigma = 1.0, population_size=50, f_scale=10.0で固定。最適化手法をcmaかlsqから選べるようにするだけで十分。
- to_geotiff
    - 出力パス: ファイルエクスプローラで指定できるようにする。
    - resolution: 1.0: 出力するGeoTIFFファイルの空間解像度(m)
    - crs: DSM/AirborneのCRSと同じで固定。選択不要。
    - interpolate: True
    - max_dist: resolutionと同じ値を自動入力: 穴埋めする最大バッファ(m)
    - agg_func: mean固定。選択不要。