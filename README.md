# The Morning Ledger, public site

Live site: https://themorningledgerr.netlify.app/

Each morning the daily run adds `editions/YYYY-MM-DD.html`, then commits and pushes. Netlify runs `python3 build.py` and publishes `public/`:
- `/` today's edition, `/YYYY-MM-DD/` each edition, `/archive/` search by keyword or date.
- Analytics: put the Microsoft Clarity project ID in `clarity_id.txt`.
