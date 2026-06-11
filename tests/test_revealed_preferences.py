"""Tests for module 2.3.2 - revealed-preferences crossing."""
from server.pipeline.revealed_preferences import learn_revealed_preferences


def test_distributions_and_means_are_built(history):
    trait_dist, vas_mean = learn_revealed_preferences(history)

    # Every feature distribution sums to ~1.
    for feature, dist in trait_dist.items():
        if dist:
            assert abs(sum(dist.values()) - 1.0) < 1e-9

    # The latent-liked feature should have a higher mean VAS than the disliked one.
    assert vas_mean["interest:travel"] > vas_mean["interest:finance"]


def test_liked_feature_associates_with_positive_trait(history):
    trait_dist, _ = learn_revealed_preferences(history)
    # 'travel' dates were seeded to skew funny/flowing.
    assert trait_dist["interest:travel"].get("מצחיק", 0) > 0
    # 'finance' dates were seeded to skew boring.
    assert trait_dist["interest:finance"].get("משעמם", 0) > 0
