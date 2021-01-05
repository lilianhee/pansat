"""
pansat.products.soundings.igra
=======================================

This module defines the IGRA product class, which represents the global data product of radiosoundings: IGRA.


"""

import re
import os
from datetime import datetime, timedelta, date
from pathlib import Path
import pansat.download.providers as providers
from pansat.products.product import Product
import pandas as pd
from math import radians, cos, sin, asin, sqrt
import zipfile


class NoAvailableProviderError(Exception):
    """
    Exception indicating that no suitable provider could be found for
    a product.
    """


class IGRASoundings(Product):
    """
    The IGRA reanalysis class defines a generic interface for IGRA products.

    Attributes:
        name(``str``): name of product
        locations(pd.DataFrame): pandas dataframe with metadata on stations
                            (contains location ID, coordinates, and time period)

        station(``pd.DataFrame``): pandas dataframe with metadata for chosen station
        variable(``str`` ): variable to extract, if no station is given
    """

    name = "igra-soundings"

    def __init__(self, location=None, variable=None):
        """
        Args:

        location(``str`` or tuple): station name or tuple with closest coordinates as float or int (lat,lon)

        variable(``str`` ): variable to extract, if given monthly data of all stations will be downloaded

        -- available variables:--
        ghgt = Geopotential height
        temp = Temperature
        uwnd = Zonal wind component
        vapr = Vapor pressure
        vwnd = Meridional wind component
        -----------------------------------
        """

        provider = self._get_provider()
        provider = provider(self)

        destination = self.default_destination
        destination.mkdir(parents=True, exist_ok=True)
        # download meta data of all locations
        downloaded = provider.download(
            start=0,
            end=0,
            destination=destination,
            base_url="ftp.ncdc.noaa.gov",
            product_path="/pub/data/igra/",
            files=["igra2-station-list.txt"],
        )

        self.variable = variable
        self.station = location

        # pandas data frame with all locations and meta information
        self.locations = self.get_metadata()

        # define column names of pandas dataframe with station info
        colnames = [
            "ID",
            "lat",
            "lon",
            "elevation [m]",
            "name",
            "start year",
            "end year",
            "# soundings in record",
        ]
        self.locations.columns = colnames

        if self.station is None:
            self.filename_regexp = re.compile(str(self.variable) + ".*" + r".txt.zip")

        else:
            if isinstance(location, str):
                self.station = self.locations[self.locations.name == location]
            else:
                self.station = self.locations[
                    self.locations.name == self.find_nearest(location[0], location[1])
                ]
                self.filename_regexp = re.compile(
                    str(self.station.ID.values[0]) + ".*" + r".txt.zip"
                )

    def get_metadata(self):
        """Extracts data from meta data station inventory."""
        locations = pd.read_fwf(
            str(self.default_destination) + "/igra2-station-list.txt",
            sep="/s",
            engine="python",
            header=None,
        )
        return locations

    def dist(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        # Radius of earth in kilometers is 6371
        km = 6371 * c
        return km

    def find_nearest(self, lat, lon):
        """Find location of closest station to a given set of coordinates.  """
        distances = self.locations.apply(
            lambda row: self.dist(lat, lon, row["lat"], row["lon"]), axis=1
        )
        return self.locations.loc[distances.idxmin(), "name"]

    def matches(self, filename):
        """
        Determines whether a given filename matches the pattern used for
        the product.
        Args:
            filename(``str``): The filename
        Return:
            True if the filename matches the product, False otherwise.
        """
        return self.filename_regexp.match(filename)

    def filename_to_date(self, filename):
        """
        Extract timestamp from filename.
        Args:
            filename(``str``): Filename of a NCEP product.
        Returns:
            ``datetime`` object representing the timestamp of the
            filename.
        """
        filename = os.path.basename(filename)
        filename = filename.split(".")[-2]
        pattern = "%Y"

        return datetime.strptime(filename, pattern)

    def _get_provider(self):
        """ Find a provider that provides the product. """
        available_providers = [
            p
            for p in providers.ALL_PROVIDERS
            if str(self) in p.get_available_products()
        ]
        if not available_providers:
            raise NoAvailableProviderError(
                f"Could not find provider for the product {IGRASoundings.name}."
            )
        return available_providers[0]

    @property
    def default_destination(self):
        """
        The default destination for IGRA product is
        ``IGRA/<product_name>``>
        """
        return Path("IGRA") / Path(IGRASoundings.name)

    def get_filename(self, product_path):
        """Get filename for specific station

        Returns:
        filename(str): filename for download
        """

        if self.variable != None:
            fname = [
                self.variable + "_00z-mly.txt.zip",
                self.variable + "_12z-mly.txt.zip",
            ]

            if "upd" in str(product_path):
                yearmon = str(date.today().year) + str(date.today().month - 1)
                fname = [
                    self.variable + "_00z-mly-" + yearmon + ".txt.zip",
                    self.variable + "_12z-mly-" + yearmon + ".txt.zip",
                ]

        elif "2yd" in product_path:
            fname = [str(self.station["ID"].values[0]) + "-data-beg2018.txt.zip"]

        else:
            fname = [str(self.station["ID"].values[0]) + "-data.txt.zip"]

        return fname

    def download(self, period=None, destination=None, provider=None):
        """
        Download IGRA sounding data for a given station.

        Args:

        period(``str``): 'recent' to download only past 1-2 years instead of full period (last month for monthly data)
        destination(``str`` or ``pathlib.Path``): The destination where to store
                 the output data.
        Returns:

        downloaded(``list``): ``list`` with names of all downloaded files for respective data product

        """
        if self.variable != None:
            path = "/pub/data/igra/monthly/monthly-"
            if period == "recent":
                product_path = path + "upd/"
            else:
                product_path = path + "por/"
        else:
            path = "/pub/data/igra/data/data-"
            if period == "recent":
                product_path = path + "2yd/"
            else:
                product_path = path + "por/"

        if not provider:
            provider = self._get_provider()
        if not destination:
            destination = self.default_destination
        else:
            destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)

        provider = provider(self)
        filename = self.get_filename(product_path)

        downloaded = provider.download(
            start=0,
            end=0,
            destination=destination,
            base_url="ftp.ncdc.noaa.gov",
            product_path=product_path,
            files=filename,
        )

        return downloaded

    def open_monthly(self, filename):
        """
        Reads in data from monthly radiosoundings at all stations.

        """
        df = pd.read_fwf(filename)
        df.columns = [
            "Station",
            "Year",
            "Month",
            "Level [hPa]",
            "Value [$^\circ$C/10, m s$^{-1}$ or Pa]",
            "Num",
        ]
        return df

    def open_station(self, filename):
        """

        Reads in data for different variables from one sounding station. This can take some time,
        but afterwards the pandas dataframe is saved as a csv file which can be quickly be opened again.

        """

        columns = [
            "datetime",
            "LVLTYP1",
            "LVLTYP2",
            "ETIME",
            "PRESS",
            "PFLAG",
            "GPH",
            "ZFLAG",
            "T",
            "TFLAG",
            "RH",
            "DPDP",
            "WDIR",
            "WSPD",
        ]
        df = pd.DataFrame(columns=columns)
        rowidx = 0

        with open(filename) as input_file:
            for row in input_file:
                rowidx += 1
                values = row.split()
                if len(values) == 9:
                    if "#" in values[0]:
                        date = datetime.datetime(
                            int(values[1]),
                            int(values[2]),
                            int(values[3]),
                            int(values[4]),
                        )
                    else:
                        # check for flags in variable values
                        if "A" in values[2] or "B" in values[2]:
                            press = values[2][:-1]
                            pflag = values[2][-1]
                        else:
                            press = values[2]
                            pflag = ""

                        if "A" in values[3] or "B" in values[3]:
                            z = values[3][:-1]
                            zflag = values[3][-1]
                        else:
                            z = values[3]
                            zflag = ""

                        if "A" in values[4] or "B" in values[4]:
                            temp = values[4][:-1]
                            tflag = values[4][-1]
                        else:
                            temp = values[4]
                            tflag = ""

                        rows = [
                            date,
                            values[0][0],
                            values[0][1],
                            values[1],
                            press,
                            pflag,
                            z,
                            zflag,
                            temp,
                            tflag,
                            values[5],
                            values[6],
                            values[7],
                            values[8],
                        ]
                        df.loc[rowidx, :] = rows

            df.to_csv(os.path.splitext(filename)[0] + ".csv")

    def open(self, filename, advanced=False):

        """Unzips and opens a text file containing IGRA sounding data.

        Args:
        filename(``str``): name of the file to be opened
        advanced: if True, a formatted csv file will be produced from the data (only for data per station)

        Returns:
        dataframe(pandas.DataFrame): table as pandas dataframe object
        """
        # unzip downloaded file
        with zipfile.ZipFile(filename, "r") as zip_ref:
            targetdir = Path(filename).parent
            zip_ref.extractall(targetdir)

        # open monthly file format
        fname_to_open = os.path.splitext(filename)[0]
        df = self.open_monthly(fname_to_open)

        if advanced == True:
            df = self.open_stations(fname_to_open)

        return df
