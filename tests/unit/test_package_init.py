def test_package_import_succeeds_without_platform_side_effects() -> None:
    import eidp

    assert eidp.__doc__ == "Education Institution Data Pipeline."
