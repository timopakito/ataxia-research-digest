from datetime import date

from dotenv import load_dotenv

from src import pdf, state, summarize
from src.collectors import clinicaltrials, news, pubmed
from src.config import load_sources

COLLECTORS = {
    "pubmed": pubmed.collect,
    "clinicaltrials": clinicaltrials.collect,
    "news": news.collect,
}


def main():
    load_dotenv(override=True)
    config = load_sources()
    seen = state.load_state()

    new_items_by_source = {}
    total_new = 0
    for source, collect_fn in COLLECTORS.items():
        items = collect_fn(config)
        new_items = state.filter_new(items, seen.get(source, []))
        new_items_by_source[source] = new_items
        total_new += len(new_items)
        print(f"{source}: {len(items)} found, {len(new_items)} new")

    if total_new == 0:
        print("Nothing new this week, skipping summary and PDF.")
        return

    digest = summarize.build_digest(new_items_by_source)
    title = f"Veille ataxies cérébelleuses — semaine du {date.today().isoformat()}"

    output_path = pdf.render_pdf(digest, title)
    print(f"Digest written to {output_path} ({total_new} new items).")

    for source, new_items in new_items_by_source.items():
        seen.setdefault(source, [])
        state.mark_seen(seen[source], new_items)
    state.save_state(seen)


if __name__ == "__main__":
    main()
