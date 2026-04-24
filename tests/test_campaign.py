import subprocess


def test_campaign_help_runs():
    result = subprocess.run(["solo-campaign", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Scaffold a new solo RPG campaign folder" in result.stdout


def test_campaign_module_imports():
    from solo_roll import campaign
    assert callable(campaign.main)
