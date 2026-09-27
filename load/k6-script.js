import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const complaintsCreated = new Counter('complaints_created');

// Target host can be overridden via TARGET_URL environment variable
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 VUs (baseline traffic)
    { duration: '1m',  target: 50 },  // Ramp up to 50 VUs (load spike to trigger HPA scaling)
    { duration: '2m',  target: 100 }, // Sustained heavy load to test autoscale limits
    { duration: '30s', target: 10 },  // Ramp down
    { duration: '15s', target: 0 },   // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should complete within 2s
    errors: ['rate<0.1'],              // Error rate should stay below 10%
  },
};

const SAMPLE_COMPLAINTS = [
  { text: 'Water main break on 4th Avenue causing severe localized street flooding', location: '4th Avenue and Pine Street' },
  { text: 'Transformer smoking and sparking violently following heavy thunderstorm', location: 'Commercial Plaza, Block B' },
  { text: 'Deep pothole on arterial road damaging vehicle rims and tires during rush hour', location: 'Expressway Exit 14' },
  { text: 'Garbage dumpsters overflowing near municipal school generating foul odor', location: 'Sector G-10 School Road' },
  { text: 'Streetlights on entire boulevard non-operational creating severe safety hazard', location: 'Main Boulevard, Sector F-7' },
];

export default function () {
  const headers = { 'Content-Type': 'application/json' };

  // 1. Check Liveness Probe (GET /health)
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  // 2. Fetch Cached Statistics (GET /api/stats)
  const statsRes = http.get(`${BASE_URL}/api/stats`);
  check(statsRes, {
    'stats status is 200': (r) => r.status === 200,
    'stats returns json': (r) => r.headers['Content-Type'] && r.headers['Content-Type'].includes('application/json'),
  });

  // 3. Browse Complaints List (GET /api/complaints?page=1&page_size=10)
  const listRes = http.get(`${BASE_URL}/api/complaints?page=1&page_size=10`);
  check(listRes, {
    'complaints list status is 200': (r) => r.status === 200,
  });

  // 4. Submit Complaint (POST /api/complaints) — ~30% of requests simulate user intake
  if (Math.random() < 0.3) {
    const randomComplaint = SAMPLE_COMPLAINTS[Math.floor(Math.random() * SAMPLE_COMPLAINTS.length)];
    const payload = JSON.stringify({
      text: `${randomComplaint.text} [run-${__VU}-${__ITER}]`,
      location: randomComplaint.location,
    });

    const postRes = http.post(`${BASE_URL}/api/complaints`, payload, { headers });
    const success = check(postRes, {
      'complaint intake status is 201 or 429': (r) => r.status === 201 || r.status === 429,
    });

    if (postRes.status === 201) {
      complaintsCreated.add(1);
    } else if (postRes.status !== 429) {
      errorRate.add(1);
    }
  }

  // Realistic user pacing between actions
  sleep(Math.random() * 0.5 + 0.2);
}
