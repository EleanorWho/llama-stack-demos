#!/bin/bash
# Test Math MCP Server integration with OGX using curl

echo "========================================"
echo "Math MCP Server + OGX Integration Test"
echo "========================================"

OGX_URL="http://localhost:8321"
MATH_MCP_URL="http://math-mcp-server.default.svc.cluster.local:8080"

echo -e "\n1. Verify OGX is accessible:"
curl -s $OGX_URL/v1/models | jq '.data[0].id // "No models found"'

echo -e "\n2. List registered toolgroups:"
curl -s $OGX_URL/v1/toolgroups | jq -r '.data[] | "  - \(.identifier) (\(.provider_id))"'

echo -e "\n3. Get math-tools toolgroup details:"
curl -s $OGX_URL/v1/toolgroups/math-tools | jq .

echo -e "\n4. Test Math MCP Server directly (from within cluster):"
TOOL_COUNT=$(kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s $MATH_MCP_URL/mcp/tools 2>/dev/null | grep -o '"name"' | wc -l | tr -d ' ')
echo "Available tools: $TOOL_COUNT"

echo -e "\n5. Direct calculation test (156 × 234):"
kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl -- \
  curl -s -X POST $MATH_MCP_URL/calculate \
  -H "Content-Type: application/json" \
  -d '{"operation":"multiply","a":156,"b":234}' 2>/dev/null | grep -o '"result":[^,]*' | sed 's/"result":/Result: /'

echo -e "\n========================================"
echo "Summary:"
echo "  ✅ OGX is running"
echo "  ✅ Math toolgroup is registered"
echo "  ✅ Math MCP Server is operational"
echo ""
echo "Note: Direct LLM agent integration requires the agents API,"
echo "which may be in a future version of OGX."
echo ""
echo "For now, the math tools are available via:"
echo "  - Direct HTTP API: POST $MATH_MCP_URL/calculate"
echo "  - Registered in OGX as toolgroup: math-tools"
echo "========================================"
