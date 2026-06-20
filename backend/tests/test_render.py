import asyncio
from pathlib import Path
from pipeline.nodes.asset_renderer import render_flyer, render_social_card

TEST_STATE = {
  'job_id': 'test-render',
  'url': 'https://stripe.com',
  'brand_name': 'Stripe',
  'brand_category': 'Fintech',
  'brand_tone': 'professional',
  'target_audience': 'Developers and finance teams',
  'brand_promise': 'Financial infrastructure for the internet',
  'brand_colors': {
    'primary': '#635bff',
    'secondary': '#0a2540',
    'accent': '#00d4ff',
    'background': '#ffffff',
    'text': '#425466',
  },
  'usps': [
    'Accept payments in 135+ currencies',
    '99.999% uptime guaranteed',
    'Developer-first API with 5ms latency',
    'Built-in fraud detection and compliance',
  ],
  'copy_output': {
    'headlines': {
      'bold': ['Payments built for growth'],
      'professional': ['Global financial infrastructure'],
    },
    'taglines': {
      'professional': ['Financial infrastructure to grow your revenue'],
    },
    'call_to_actions': { 'bold': ['Start building'] },
    'tagline': 'Financial infrastructure for the internet',
    'elevator_pitch': 'Stripe helps businesses accept payments, scale faster, and manage revenue operations globally with developer-first tools and 135+ currency support.',
    'usp_titles': [
      'Global Payments', 'Zero Downtime',
      'Developer API', 'Fraud Protection',
    ],
    'usp_descriptions': [
      'Accept payments in 135+ currencies with local payment methods',
      '99.999% historical uptime with real-time monitoring',
      'Clean REST API with SDKs in 8 languages',
      'Radar ML fraud detection built into every transaction',
    ],
  },
  'layout_output': {
    'brand_category_tag': 'Fintech',
    'visual_style': 'corporate',
  },
}

async def test():
  out = Path('outputs/test-render/assets')
  out.mkdir(parents=True, exist_ok=True)
  flyer  = await render_flyer(TEST_STATE, out)
  social = await render_social_card(TEST_STATE, out)
  print(f'Flyer:  {flyer}')
  print(f'Social: {social}')
  print('Open these files to verify quality.')

asyncio.run(test())
