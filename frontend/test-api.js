// Simple API test script
const API_BASE = 'http://localhost:8001';

async function testAPI() {
  console.log('🧪 Testing GraphRAG API connection...');

  try {
    // Test health endpoint
    console.log('📊 Testing health endpoint...');
    const healthResponse = await fetch(`${API_BASE}/health`);
    const healthData = await healthResponse.json();
    console.log('✅ Health check:', healthData);

    // Test system status
    console.log('📈 Testing system status...');
    const statusResponse = await fetch(`${API_BASE}/system/status`);
    const statusData = await statusResponse.json();
    console.log('✅ System status:', statusData);

    // Test query endpoint (will likely fail due to missing data)
    console.log('🤖 Testing query endpoint...');
    const queryResponse = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: 'What is GraphRAG?'
      })
    });
    const queryData = await queryResponse.json();
    console.log('✅ Query response:', queryData);

    console.log('🎉 All API tests completed!');

  } catch (error) {
    console.error('❌ API test failed:', error);
  }
}

testAPI();
