# PySceneDetect AdaptiveDetector – Python API Guide

## 1. Installation
```bash
pip install "scenedetect[opencv]"
```

## 2. Basic Usage
```python
from scenedetect import detect, AdaptiveDetector

scene_list = detect("input.mp4", AdaptiveDetector())

for i, (start, end) in enumerate(scene_list):
    print(f"Scene {i+1}: {start.get_timecode()} -> {end.get_timecode()}")
```

## 3. What AdaptiveDetector Does
AdaptiveDetector performs:
1. Pass 1 — compute HSV frame differences (same as ContentDetector).
2. Pass 2 — compute adaptive deviation using a rolling average.
3. A cut triggers when:
   - adaptive_ratio > adaptive_threshold  
   - content_val > min_content_val

## 4. Constructor Parameters
```python
AdaptiveDetector(
    adaptive_threshold=3.0,
    min_scene_len=15,
    window_width=2,
    min_content_val=15.0,
    weights=Components(...),
    luma_only=False
)
```

### Main Parameters
- **adaptive_threshold**: Higher = fewer cuts.
- **min_scene_len**: Minimum frames between detected cuts.
- **window_width**: Number of preceding/following frames used for smoothing.
- **min_content_val**: Minimum absolute change required.
- **weights**: Control hue/saturation/luma sensitivity.

## 5. Tuning Examples

### A. Default Balanced Setup
```python
AdaptiveDetector(adaptive_threshold=3.0, min_scene_len=15, min_content_val=15)
```

### B. More Sensitive
```python
AdaptiveDetector(adaptive_threshold=2.0, min_scene_len=10, min_content_val=10)
```

### C. More Robust to Motion
```python
AdaptiveDetector(
    adaptive_threshold=4.0,
    min_scene_len=30,
    window_width=3,
    min_content_val=20
)
```

## 6. Advanced API (SceneManager)
```python
from scenedetect import SceneManager, StatsManager
from scenedetect.video_manager import VideoManager
from scenedetect.detectors import AdaptiveDetector

video_manager = VideoManager(["input.mp4"])
stats_manager = StatsManager()
scene_manager = SceneManager(stats_manager)

scene_manager.add_detector(AdaptiveDetector())

video_manager.start()
scene_manager.detect_scenes(video_manager)

scenes = scene_manager.get_scene_list()
```

## 7. Exporting Metrics for Debugging
```python
stats_manager.save_to_csv("stats.csv")
```

## 8. Splitting Video with FFmpeg
```python
from scenedetect import split_video_ffmpeg
split_video_ffmpeg("input.mp4", scenes, output_dir="scenes")
```

## 9. Cheat Sheet
- Use `detect("file.mp4", AdaptiveDetector())` for quick use.
- Tune:
  - `adaptive_threshold` = sensitivity
  - `min_scene_len` = avoid rapid flicker
  - `window_width` = smooth context
  - `min_content_val` = absolute threshold

