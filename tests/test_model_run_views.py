"""Full-size run responses must fit the real gateway and preserve every manifest byte."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastmcp import Client

from regulatory_mcp.analysis.run_views import manifest_page
from regulatory_mcp.application import create_application
from regulatory_mcp.config import Settings
from regulatory_mcp.contracts import EconomicModel
from regulatory_mcp.evidence import EvidenceStore, StoreError


def large_model():
    return EconomicModel(
        title="97-formula response regression",
        baseline="Synthetic baseline",
        alternative="Synthetic alternative",
        affected_population="Synthetic population",
        dollar_year=2014,
        monetary_basis="real",
        timing_convention="Year zero",
        created_at=datetime.now(UTC),
        parameters=[
            dict(
                name="base",
                value="1",
                unit=[],
                entity_definition="Synthetic",
                basis="assumption",
                rationale="Synthetic input",
            )
        ],
        formulas=[
            dict(
                name=f"step_{i}",
                operation="add",
                operands=[f"step_{i - 1}" if i else "base", "base"],
                unit=[],
                rationale="Synthetic formula explanation. " * 20,
            )
            for i in range(97)
        ],
        outputs=["step_96"],
    )


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_large_run_and_comparison_roundtrip(tmp_path, mode):
    async def run():
        store = EvidenceStore(tmp_path)
        model = large_model()
        store.save_model(model)
        app = await create_application(Settings(gateway_mode=mode), store)
        async with Client(app) as client:

            async def call(name, args):
                if mode == "codemode":
                    response = await client.call_tool(
                        "execute", {"code": f"return await call_tool({name!r}, {args!r})"}
                    )
                else:
                    response = await client.call_tool(name, args)
                return response.structured_content

            result = await call("analysis_evaluate_model", {"model_id": str(model.model_id)})
            assert Decimal(result["outputs"]["step_96"]) == 98
            assert result["manifest_included"] is False
            assert result == await call("analysis_get_model_run", {"run_id": result["run_id"]})
            comparison = await call(
                "analysis_reconcile_model_output",
                {
                    "request": {
                        "run_id": result["run_id"],
                        "output_name": "step_96",
                        "reported": dict(
                            name="reported",
                            value="98",
                            unit="1",
                            entity_definition="Synthetic population",
                            basis="assumption",
                            assumption_rationale="Synthetic expected result",
                        ),
                    }
                },
            )
            assert comparison["outputs"]["within_tolerance"]
            for item in (result, comparison):
                text, offset, digest = "", 0, None
                while offset is not None:
                    page = await call(
                        "analysis_inspect_model_run",
                        {"run_id": item["run_id"], "offset": offset, "limit": 4000},
                    )
                    assert page["offset"] == offset and len(page["text"]) <= 4000
                    digest = digest or page["sha256"]
                    assert digest == page["sha256"]
                    text += page["text"]
                    offset = page["next_offset"]
                assert hashlib.sha256(text.encode("ascii")).hexdigest() == digest
                expected = store.run(UUID(item["run_id"])).model_dump(mode="json")
                assert json.loads(text) == expected
                assert len(text) > 32000
            with pytest.raises(StoreError, match="offset exceeds"):
                manifest_page(store, UUID(result["run_id"]), 10**9, 1)

    asyncio.run(run())
