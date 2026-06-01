"""Example custom metric plugin."""


def score(image_ctx, response, ground_truth):
    """Score based on whether response contains 'defect'."""
    passed = "defect" in response.lower()
    return {
        "score": 1.0 if passed else 0.0,
        "passed": passed,
        "details": {"response_length": len(response)},
    }
