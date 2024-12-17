## Blockchain Deadlines

Deadline countdowns for high-quality academic venues relevant to blockchain research.

Forked from [aideadlin.es](https://aideadlin.es/) originally developed by [abhshkdz](https://twitter.com/abhshkdz).


## Contributing

**Contributions are very welcome!**

To add or update a deadline:
- Fork the repository
- Update/create the respective file in `_data/conferences_raw`
- Make sure each cycle of the conference has the `title`, `year`, `id`, `link`, `deadline`, `timezone`, `date`, `place`, `sub` attributes
    + See available timezone strings [here](https://momentjs.com/timezone/). Anywhere-on-earth usually refers to `Etc/GMT+12`.
    + If there are multiple deadlines (e.g., for abstract and submission), use the *earliest* deadline as `deadline` and describe details in `note`.
- Optionally add a `note` (e.g., for submission deadline, if the earliest deadline is for abstracts only; or submission cycle)
- Optionally add `hindex` (refers to h5-index from [here](https://scholar.google.com/citations?view_op=top_venues&vq=eng))
- Example:
    ```yaml
    - title: BestConf
      year: 2022
      id: bestconf22b  # title as lower case + last two digits of year [+ optional: cycle]
      full_name: Best Conference for Anything  # full conference name
      link: link-to-website.com
      deadline: YYYY-MM-DD HH:SS
      timezone: Etc/GMT+12
      note: Fall cycle. Deadline for abstract registration. Paper deadline YYYY-MM-DD AoE.
      sub: BC
      place: Incheon, South Korea
      date: September, 18-22, 2022
      start: YYYY-MM-DD
      end: YYYY-MM-DD
    ```
- Run `compress-conferences.sh` to update `_data/conferences.yml`
- Send a pull request

If you want to help out with **updating existing-but-outdated deadlines to next-year's edition**, check out [`chatgpt-updater.py`](chatgpt-updater.py).
It uses ChatGPT and Serper to update the YAML files (semi-)automatically. It expects API keys in the environment variables `OPENAI_API_KEY` and `SERPER_API_KEY`. It can also, optionally when the environment variable `COLLECT_TRAINING_DATA` is set, record its interactions to local files, to collect training data for model fine-tuning in the future.
It doesn't always work perfectly, so please double check the output with the conference website before submitting a pull request, but it worked astonishingly well and sped the work up by quite a bit.
See [this thread on X](https://x.com/jneu_net/status/1868995269691588672) for a bit more context.
**Improvements to the prompt and/or script are very welcome!**


## License

This project is licensed under [MIT](https://abhshkdz.mit-license.org/).

It uses:
- [IcoMoon Icons](https://icomoon.io/#icons-icomoon): [GPL](http://www.gnu.org/licenses/gpl.html) / [CC BY4.0](http://creativecommons.org/licenses/by/4.0/)
