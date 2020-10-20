"""
Tests for the pansat.products.reanalysis.era5 module.
"""


from datetime import datetime
import os
import pytest
import pansat.products.reanalysis.era5 as era5


PRODUCTS = [era5.ERA5Product('reanalysis-era5-single-levels-monthly-means', ['2m_temperature'])]

TEST_NAMES = {'reanalysis-era5-single-levels-monthly-means': 'era5-reanalysis-era5-single-levels-monthly-means_20161000:00_2m_temperature.nc'}

TEST_TIMES = {'reanalysis-era5-single-levels-monthly-means': datetime(2018, 5, 23, 00, 41, 15)}



@pytest.mark.parametrize("product", PRODUCTS)
def test_filename_to_date(product):
    """
    Assert that time is correctly extracted from filename.
    """
    filename = TEST_NAMES[product.name]
    time = product.filename_to_date(filename)
    assert time == TEST_TIMES[product.name]


HAS_PANSAT_PASSWORD = "PANSAT_PASSWORD" in os.environ


@pytest.mark.skipif(not HAS_PANSAT_PASSWORD, reason="Pansat password not set.")
@pytest.mark.usefixtures("test_identities")
def test_download():
    product = PRODUCTS[0]
    t_0 = datetime(2018, 6, 1, 10)
    t_1 = datetime(2018, 7, 1, 12)
    product.download(t_0, t_1)





