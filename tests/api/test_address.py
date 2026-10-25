"""Exercise the HTTP boundary used to validate and repair addresses."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.yasno_outages.api import (
    YasnoApi,
    YasnoApiError,
    YasnoNotFoundError,
)
from custom_components.yasno_outages.api.const import (
    GROUP_BY_ADDRESS_ENDPOINT,
    HOUSES_ENDPOINT,
    STREETS_ENDPOINT,
)


@pytest.fixture
def http_response():
    with patch("aiohttp.ClientSession.get") as get:
        response = AsyncMock()
        response.raise_for_status = MagicMock()
        get.return_value.__aenter__.return_value = response
        yield get, response


async def test_address_lookup_parameters_and_group(http_response):
    get, response = http_response
    response.json.return_value = {"group": 29, "subgroup": 1}
    group = await YasnoApi().fetch_group_by_address(1, 2, 10, 20)
    assert group == "29.1"
    assert get.call_args.args == (GROUP_BY_ADDRESS_ENDPOINT,)
    assert get.call_args.kwargs["params"] == {
        "regionId": 1,
        "dsoId": 2,
        "streetId": 10,
        "houseId": 20,
    }


@pytest.mark.parametrize(
    "payload", [[], {}, {"group": 1}, {"group": None, "subgroup": 1}]
)
async def test_invalid_group_response_is_not_stale_address(http_response, payload):
    _, response = http_response
    response.json.return_value = payload
    with pytest.raises(YasnoApiError) as error:
        await YasnoApi().fetch_group_by_address(1, 2, 10, 20)
    assert not isinstance(error.value, YasnoNotFoundError)


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
async def test_only_http_not_found_is_classified_as_stale(http_response, status):
    _, response = http_response
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        request_info=MagicMock(),
        history=(),
        status=status,
    )
    with pytest.raises(YasnoApiError) as error:
        await YasnoApi().fetch_group_by_address(1, 2, 10, 20)
    assert isinstance(error.value, YasnoNotFoundError) == (status == 404)


@pytest.mark.parametrize("method", ["fetch_streets", "fetch_houses"])
@pytest.mark.parametrize("valid_response", [True, False])
async def test_repair_lookup_response_and_parameters(
    http_response, method, valid_response
):
    get, response = http_response
    payload = [{"id": 10, "value": "Test"}]
    response.json.return_value = payload if valid_response else {}
    params = {"region_id": 1, "provider_id": 2, "query": "Test"}
    expected_params = {"regionId": 1, "dsoId": 2, "query": "Test"}
    endpoint = STREETS_ENDPOINT
    if method == "fetch_houses":
        params["street_id"] = 10
        expected_params["streetId"] = 10
        endpoint = HOUSES_ENDPOINT
    lookup = getattr(YasnoApi(), method)
    if valid_response:
        assert await lookup(**params) == payload
    else:
        with pytest.raises(YasnoApiError):
            await lookup(**params)
    assert get.call_args.args == (endpoint,)
    assert get.call_args.kwargs["params"] == expected_params


async def test_missing_lookup_ids_do_not_make_http_requests(http_response):
    get, _ = http_response
    api = YasnoApi()
    assert await api.fetch_streets(None, 2, "Test") == []
    assert await api.fetch_houses(1, 2, None, "Test") == []
    assert await api.fetch_group_by_address(1, 2, 10, None) is None
    get.assert_not_called()
