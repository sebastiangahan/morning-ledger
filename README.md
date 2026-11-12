# The Morning Ledger, public site

Live site: https://morning-ledger.sebastiangahan.workers.dev/

Each morning the daily run adds `editions/YYYY-MM-DD.html`, then commits and pushes. Cloudflare Workers runs `python3 build.py` and serves `public/` (see wrangler.jsonc). Netlify is retired:
- `/` today's edition, `/YYYY-MM-DD/` each edition, `/archive/` search by keyword or date.
- Analytics: put the Microsoft Clarity project ID in `clarity_id.txt`.
