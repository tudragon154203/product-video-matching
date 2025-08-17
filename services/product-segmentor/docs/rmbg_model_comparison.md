# RMBG Model Comparison and Usage Guide

This document provides a comparison between RMBG-1.4 and RMBG-2.0 models and explains how to use both in the product-segmentor service.

## Model Overview

### RMBG-1.4
- **Model**: `briaai/RMBG-1.4`
- **Parameters**: 44.1M
- **Training**: 12,000+ professional images
- **Use Case**: General background removal with good performance on e-commerce and advertising images
- **Output**: Raw logits requiring sigmoid activation
- **Normalization**: `[0.5, 0.5, 0.5]` for both mean and standard deviation

### RMBG-2.0
- **Model**: `briaai/RMBG-2.0`
- **Parameters**: Larger architecture (improved over 1.4)
- **Training**: Enhanced dataset and training methodology
- **Use Case**: State-of-the-art background removal with improved accuracy across various image types
- **Output**: Already processed with sigmoid activation
- **Normalization**: `[0.485, 0.456, 0.406]` for mean and `[0.229, 0.224, 0.225]` for standard deviation

## Key Differences

| Feature | RMBG-1.4 | RMBG-2.0 |
|---------|----------|----------|
| Model Architecture | 44.1M parameters | Enhanced architecture |
| Output Processing | Raw logits (requires sigmoid) | Pre-processed (sigmoid applied) |
| Normalization | Mean: [0.5, 0.5, 0.5]<br>Std: [0.5, 0.5, 0.5] | Mean: [0.485, 0.456, 0.406]<br>Std: [0.229, 0.224, 0.225] |
| Performance | Good for general use | Improved accuracy across all categories |
| Training Data | 12,000+ professional images | Enhanced dataset and methodology |

## Usage

### Configuration

The product-segmentor service supports both models through configuration. Set the `SEGMENTATION_MODEL_NAME` in your `.env` file:

```bash
# For RMBG-2.0 (default)
SEGMENTATION_MODEL_NAME=briaai/RMBG-2.0

# For RMBG-1.4
SEGMENTATION_MODEL_NAME=briaai/RMBG-1.4
```

### Programmatic Usage

```python
from services.segmentor_factory import create_segmentor

# Create RMBG-2.0 segmentor (default)
segmentor_2_0 = create_segmentor("briaai/RMBG-2.0")

# Create RMBG-1.4 segmentor
segmentor_1_4 = create_segmentor("briaai/RMBG-1.4")

# Initialize and use
await segmentor_1_4.initialize()
mask = await segmentor_1_4.segment_image("path/to/image.jpg")
segmentor_1_4.cleanup()
```

### Case-Insensitive Support

The factory supports case-insensitive model names:

```python
# All of these work:
segmentor = create_segmentor("briaai/RMBG-1.4")
segmentor = create_segmentor("BriaAI/RMBG-1.4")
segmentor = create_segmentor("briaai/rmbg-1.4")
```

## Performance Considerations

### RMBG-1.4
- **Pros**: 
  - Faster inference time
  - Lower memory footprint
  - Good for batch processing
- **Cons**:
  - Slightly lower accuracy than RMBG-2.0
  - Requires additional sigmoid processing

### RMBG-2.0
- **Pros**:
  - Higher accuracy
  - Better handling of complex backgrounds
  - State-of-the-art performance
- **Cons**:
  - Slower inference time
  - Higher memory requirements

## Choosing the Right Model

### Use RMBG-1.4 when:
- Processing speed is critical
- Working with well-lit, simple backgrounds
- Memory constraints are a concern
- Batch processing large volumes of images

### Use RMBG-2.0 when:
- Accuracy is the top priority
- Working with complex backgrounds
- Processing high-value images
- Best quality is required regardless of processing time

## Migration Guide

### From RMBG-1.4 to RMBG-2.0
1. Update configuration: `SEGMENTATION_MODEL_NAME=briaai/RMBG-2.0`
2. No code changes required - the factory handles both models
3. Monitor performance improvements

### From RMBG-2.0 to RMBG-1.4
1. Update configuration: `SEGMENTATION_MODEL_NAME=briaai/RMBG-1.4`
2. No code changes required
3. Expect faster processing with slightly reduced accuracy

## Testing

Both models are thoroughly tested:

```bash
# Run RMBG-1.4 specific tests
python -m pytest tests/test_rmbg14_segmentor.py -v

# Run all segmentor tests
python -m pytest tests/ -v
```

## Troubleshooting

### Common Issues

1. **Model Loading Errors**
   - Ensure `HF_TOKEN` is properly configured in your environment
   - Check internet connectivity for model downloads

2. **Memory Issues**
   - RMBG-2.0 requires more memory than RMBG-1.4
   - Consider using RMBG-1.4 for memory-constrained environments

3. **Performance Differences**
   - RMBG-2.0 is slower but more accurate
   - RMBG-1.4 is faster but slightly less accurate

## Future Considerations

- RMBG-2.0 is the recommended model for new implementations
- RMBG-1.4 remains supported for legacy systems and performance-critical applications
- Monitor for future model releases and updates