"""
GovChat-NL: instellingen van het persoonsgegevensfilter bepalen en de modus
"Altijd filteren" op de server afdwingen.

Volgorde: de beheerder zet het filter aan of uit (pii.enable). Staat het aan,
dan geldt de modus van de agent (model meta 'pii_filter'), anders de
standaardmodus van de beheerder. "Altijd filteren" (mask) van de agent of
van de beheerder is bindend: een chat kan die niet uitzetten.
"""

import asyncio
import logging

from open_webui.utils.pii.detector import CATEGORIES, MODES, detect_and_mask

log = logging.getLogger(__name__)


async def get_pii_config() -> dict:
    # Hier pas importeren: zo blijft de detector zonder database te testen
    from open_webui.models.config import Config

    values = await Config.get_many('pii.enable', 'pii.default_mode', 'pii.categories')
    categories = values.get('pii.categories')
    return {
        'enable': bool(values.get('pii.enable')),
        'default_mode': values.get('pii.default_mode') if values.get('pii.default_mode') in MODES else 'warn',
        'categories': [c for c in categories if c in CATEGORIES] if isinstance(categories, list) else list(CATEGORIES),
    }


def get_model_pii_mode(model: dict | None) -> str | None:
    mode = ((model or {}).get('info') or {}).get('meta', {}).get('pii_filter')
    return mode if mode in MODES else None


async def is_mask_enforced(model: dict | None, config: dict | None = None) -> bool:
    config = config or await get_pii_config()
    if not config['enable']:
        return False
    agent_mode = get_model_pii_mode(model)
    return agent_mode == 'mask' or (agent_mode is None and config['default_mode'] == 'mask')


def _mask_message(message: dict, categories: list[str]) -> int:
    content = message.get('content')
    count = 0
    if isinstance(content, str):
        masked, replacements = detect_and_mask(content, categories)
        message['content'] = masked
        count += len(replacements)
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'text' and isinstance(part.get('text'), str):
                masked, replacements = detect_and_mask(part['text'], categories)
                part['text'] = masked
                count += len(replacements)
    return count


async def enforce_pii_mask(messages: list[dict], model: dict | None) -> list[dict]:
    """Maskeer alle gebruikersberichten als de modus 'Altijd filteren' bindend is."""
    config = await get_pii_config()
    if not await is_mask_enforced(model, config):
        return messages

    def run():
        return sum(_mask_message(m, config['categories']) for m in messages if m.get('role') == 'user')

    count = await asyncio.to_thread(run)
    if count:
        log.info('PII-filter: %d persoonsgegevens op de server gemaskeerd', count)
    return messages
