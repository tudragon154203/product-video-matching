# Product Requirements Document: PyAV Integration for AV1 Video Support

## Executive Summary

This PRD outlines the integration of PyAV library into the video-crawler service to solve the AV1 codec incompatibility issue that currently prevents frame extraction from 18.8% of YouTube videos. The solution will implement a hybrid extraction system that routes AV1-encoded videos to PyAV while maintaining existing OpenCV/PySceneDetect pipeline for other codecs.

## Problem Statement

### Current Issue
- **18.8% failure rate**: 6 out of 32 videos in job 050a9bb8-74ea-44e1-919f-a0b45126bed4 failed to extract frames
- **Root Cause**: AV1 codec incompatibility with OpenCV's FFmpeg backend
- **Impact**: Missing keyframes reduces matching quality and completeness

### Technical Analysis
- All failing videos use libdav1d (AV1) codec
- OpenCV can open containers but cannot seek or decode frames
- Error pattern: "Missing Sequence Header", "Failed to get pixel format"
- YouTube's increasing adoption of AV1 will grow this problem over time

### Validation Results
- **PyAV Success Rate**: 100% (6/6 failing videos successfully processed)
- **OpenCV Success Rate**: 0% on AV1 videos
- **Performance Trade-off**: PyAV is ~50% slower but provides 100% reliability

## Solution Overview

### Hybrid Extraction Architecture
Implement a codec-aware routing system that:
1. **Detects video codec** during validation
2. **Routes to appropriate extractor**:
   - H.264/VP9 and other non-AV1 codecs → PySceneDetect (fast, optimized)
   - AV1 → PyAV extractor (reliable, slower)
3. **Simplifies extractor surface** by retiring the legacy length-based extractor so only two code paths remain (PySceneDetect default, PyAV for AV1)
4. **Maintains backward compatibility** with existing pipeline

### Key Components
1. **PyAVKeyframeExtractor**: New extractor class for AV1 videos
2. **Codec Detection**: Video codec identification utility
3. **Smart Router**: Automatic extractor selection based on codec
4. **Fallback Chain**: Graceful degradation if PyAV fails

## Detailed Requirements

### Functional Requirements

#### FR1: Codec Detection
- Detect video codec using ffprobe or PyAV container inspection
- Support identification of: H.264 (avc), VP9, AV1 (libdav1d)
- Log codec information for debugging and monitoring

#### FR2: PyAV Keyframe Extractor
- Extract frames from AV1-encoded videos using PyAV library
- Support multi-frame extraction (1-5 frames based on duration)
- Apply same blur score filtering as existing extractor
- Maintain identical output format (timestamp, filepath) tuples

#### FR3: Smart Routing Logic
- Automatic extractor selection based on video codec
- H.264/VP9 and other non-AV1 codecs → PySceneDetect extractor
- AV1 → PyAV extractor
- Unknown codecs → try PySceneDetect first, fallback to PyAV

#### FR4: Extractor Simplification
- Retire `services/video-crawler/keyframe_extractor/length_adaptive_extractor.py` and remove the strategy option from factories/configuration
- Keep only two extractor implementations in the router: PySceneDetect and PyAV
- Drop any env vars or flags tied to the length-based strategy to shrink the maintenance surface

#### FR5: Error Handling & Fallbacks
- If PyAV extraction fails, attempt PySceneDetect as fallback
- Log detailed error information for debugging
- Return empty list only if all extractors fail
- Maintain system stability with graceful degradation

#### FR6: Configuration & Settings
- Add PyAV-specific settings to config loader with sane defaults (no new .env required)
- Remove length-based extractor settings/strategy flag
- Support quality settings (JPEG compression, frame formats) via config loader overrides
- PyAV routing enabled by default; no feature flag needed

### Non-Functional Requirements

#### NFR1: Performance
- PyAV extraction should complete within 2x the time of PySceneDetect
- Memory usage should not exceed existing limits by more than 50%
- No impact on processing of non-AV1 videos

#### NFR2: Reliability
- 99%+ success rate for AV1 video processing
- Zero impact on existing H.264/VP9 processing reliability
- Robust error handling prevents system crashes

#### NFR3: Maintainability
- Clean separation between extractors
- Shared utilities and common interface
- Comprehensive logging for debugging
- Unit tests covering all code paths

#### NFR4: Backward Compatibility
- No breaking changes to existing API
- Existing PySceneDetect extractor remains unchanged
- Configuration should be opt-in initially

## Technical Architecture

### Component Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Codec Detect  │───►│  Smart Router   │───►│ PySceneDetect   │
│   (ffprobe/PyAV)│    │   Logic         │    │ Extractor       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PyAV         │
                       │ Extractor       │
                       └─────────────────┘
```

### New Classes and Files

#### 1. PyAVKeyframeExtractor Class
```python
class PyAVKeyframeExtractor(AbstractKeyframeExtractor):
    """PyAV-based extractor for AV1 and other problematic codecs."""

    def _extract_frames_from_video(self, video_path, keyframe_dir, video_id):
        # Multi-frame extraction using PyAV
        pass

    def _detect_codec(self, video_path):
        # Codec detection using PyAV or ffprobe
        pass
```

#### 2. Smart Router Utility
```python
class ExtractorRouter:
    """Routes videos to appropriate extractor based on codec."""

    def get_extractor(self, video_path) -> AbstractKeyframeExtractor:
        # Returns appropriate extractor instance
        pass
```

#### 3. Configuration Updates
```python
class PyAVSettings:
    enable_pyav_routing: bool = True  # default on, no .env toggle required
    pyav_quality: int = 90
    pyav_format: str = "jpg"
    pyav_max_frames: int = 5
    fallback_to_pyscene: bool = True

# Router/factory options (length-based strategy removed)
SUPPORTED_EXTRACTORS = ["pyscene_detect", "pyav"]
```

### Integration Points

#### Service Integration
- Update `handlers/video_crawler.py` to use router
- Add PyAV settings to `config_loader.py`
- Update Docker container to include PyAV dependency
- Remove length-based extractor wiring from `keyframe_extractor/factory.py` and any settings documentation

#### Database Integration
- No schema changes required
- Add codec information logging for monitoring
- Track extraction method in video metadata

#### API Integration
- No breaking changes to existing endpoints
- Add codec information to job status responses
- Include extraction method in debugging logs

## Implementation Plan

### Phase 1: Foundation (1 day)
1. **Install PyAV dependency**
   - Add `av==16.0.1` to requirements.txt
   - Update Docker containers

2. **Create PyAV Extractor**
   - Implement `PyAVKeyframeExtractor` class
   - Basic frame extraction using PyAV
   - Multi-frame fallback logic

3. **Codec Detection**
   - Implement codec detection utility
   - Support for ffprobe and PyAV methods
   - Error handling for corrupted files

### Phase 2: Integration (1 day)
1. **Smart Router Implementation**
   - Create `ExtractorRouter` class
   - Integration with existing pipeline
   - Configuration-driven routing
   - Explicit mapping: AV1 → PyAV, non-AV1 → PySceneDetect (length-based option removed)

2. **Configuration & Settings**
   - Add PyAV settings to config loader
   - Remove length-based extractor settings/flags from config loader and docs
   - Keep defaults in config loader (no new .env entries required)
   - Default values and validation

3. **Error Handling**
   - Fallback chain implementation
   - Comprehensive error logging
   - Graceful degradation

4. **Extractor Retirement**
   - Delete `length_adaptive_extractor.py` and its factory strategy wiring
   - Remove any tests or fixtures that only target the retired strategy
   - Validate no call sites remain before removal

### Phase 3: Testing & Validation (0.5 day)
1. **Unit Tests**
   - Test PyAV extractor with various codecs
   - Test routing logic for all scenarios
   - Test error handling and fallbacks

2. **Integration Tests**
   - Test with real failing AV1 videos
   - Verify no impact on H.264/VP9 videos
   - Performance benchmarking

3. **Production Readiness**
   - Documentation updates
   - Monitoring and alerting
   - Rollback procedures

## Success Metrics

### Primary Metrics
- **AV1 Success Rate**: Increase from 0% to 95%+
- **Overall Success Rate**: Increase from 81.2% to 98%+
- **Processing Time**: PyAV extraction <2x PySceneDetect time

### Secondary Metrics
- **System Stability**: No increase in error rates or crashes
- **Memory Usage**: <50% increase over baseline
- **Maintainability**: Code coverage >90% for new code

## Risks and Mitigations

### Technical Risks
1. **PyAV Performance**: May be significantly slower than expected
   - *Mitigation*: Implement caching, optimize frame extraction
   - *Fallback*: Disable PyAV routing for performance-critical jobs

2. **Memory Usage**: PyAV may use more memory
   - *Mitigation*: Implement memory monitoring and limits
   - *Fallback*: Restart service if memory exceeds thresholds

3. **Compatibility**: PyAV may have platform-specific issues
   - *Mitigation*: Test across all deployment environments
   - *Fallback*: Graceful degradation to PySceneDetect

### Business Risks
1. **YouTube Format Changes**: AV1 adoption patterns may change
   - *Mitigation*: Monitor YouTube format trends
   - *Response*: Flexible routing configuration

2. **Library Maintenance**: PyAV library dependency maintenance
   - *Mitigation*: Regular dependency updates
   - *Response*: Multiple extractor options for redundancy

## Rollout Plan

### Phase 1: Development (2 days)
- Implement all components in development environment
- Comprehensive testing and validation
- Performance benchmarking

### Phase 2: Staging (0.5 day)
- Deploy to staging environment
- Test with real job data
- Performance and stability validation

### Phase 3: Production (0.5 day)
- Feature flag controlled rollout
- Monitor success rates and performance
- Full rollout after validation

### Rollback Plan
- Disable PyAV routing via configuration
- Revert to PySceneDetect-only extraction
- Monitor system stability during rollback

## Future Enhancements

### Short Term (3 months)
- **Enhanced Codec Support**: Add support for other problematic codecs
- **Performance Optimization**: GPU acceleration for PyAV extraction
- **Monitoring Dashboard**: Real-time codec success rate tracking

### Long Term (6+ months)
- **ML-Based Routing**: Predict best extractor based on video characteristics
- **Advanced Fallbacks**: Multiple fallback strategies beyond two extractors
- **Format Conversion**: On-the-fly codec conversion for problematic videos

## Conclusion

This PyAV integration will solve the critical AV1 codec incompatibility issue, improving video processing success rates from 81.2% to 98%+ while maintaining system performance and reliability. The hybrid architecture ensures backward compatibility while providing a path for future enhancements and optimizations.

The implementation is technically straightforward with clear success metrics and manageable risks. The staged rollout approach minimizes production risk while delivering immediate value to users.
