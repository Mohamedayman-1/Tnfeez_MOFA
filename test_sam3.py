from ultralytics.models.sam import SAM3VideoPredictor

# Create video predictor
overrides = dict(conf=0.25, task="segment", mode="predict", model="sam3.pt", half=True)
predictor = SAM3VideoPredictor(overrides=overrides)

# Track objects using bounding box prompts
results = predictor(source=0,stream=True)

# Process and display results
for r in results:
    r.show()  # Display frame with segmentation masks