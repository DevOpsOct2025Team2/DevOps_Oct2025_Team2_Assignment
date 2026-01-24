import pytest
from app.templates import layout

@pytest.mark.parametrize("driver", ["chrome"], indirect=True)  
def test(driver):
    layout.launchHome(driver)
    layout.login(driver)
    layout.logout(driver)