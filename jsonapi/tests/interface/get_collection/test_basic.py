import pytest

from jsonapi.tests.util import *


@pytest.mark.asyncio
async def test_no_args(users, user_count, superuser_id):
    user_id_list = sample_integers(1, user_count)
    async with get_collection({
        'filter[id]': ','.join(str(x) for x in user_id_list)
    }, users, login=superuser_id) as json:
        assert len(json['data']) > 0
        for user in json['data']:
            assert_object(user, 'user', lambda v: int(v) in user_id_list)
        assert 'included' not in json
