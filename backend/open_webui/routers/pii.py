"""
GovChat-NL: API voor het persoonsgegevensfilter.

- POST /detect: treffers in een tekst (voor de pop-up)
- POST /mask:   tekst met gemaskeerde treffers (behalve de uitgevinkte)
- GET/POST /config: instellingen voor de beheerder
"""

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.pii import CATEGORIES, LABELS, MODES, detect, mask, segments
from open_webui.utils.pii.enforcement import get_pii_config

log = logging.getLogger(__name__)

router = APIRouter()

# Maximale tekstlengte die gecontroleerd wordt (voorkomt dat heel lange plaktekst de server ophoudt)
MAX_TEXT_LENGTH = 100_000


class TextForm(BaseModel):
    text: str = Field(max_length=MAX_TEXT_LENGTH)


class MaskForm(TextForm):
    # Indexen (uit /detect) van treffers die de gebruiker heeft uitgevinkt
    exclude: list[int] = []


class PiiConfigForm(BaseModel):
    ENABLE_PII_FILTER: bool
    PII_FILTER_DEFAULT_MODE: str
    PII_FILTER_CATEGORIES: list[str]


def _serialize(findings) -> list[dict]:
    return [
        {
            'index': idx,
            'category': f.category,
            'label': LABELS.get(f.category),
            'text': f.text,
            'maskable': f.maskable,
            'detail': f.detail,
        }
        for idx, f in enumerate(findings)
    ]


@router.post('/detect')
async def detect_pii(form_data: TextForm, user=Depends(get_verified_user)):
    config = await get_pii_config()
    if not config['enable'] or not form_data.text.strip():
        return {'enabled': config['enable'], 'findings': [], 'segments': [{'text': form_data.text}]}

    findings = await asyncio.to_thread(detect, form_data.text, config['categories'])
    return {
        'enabled': True,
        'findings': _serialize(findings),
        'segments': segments(form_data.text, findings),
    }


@router.post('/mask')
async def mask_pii(form_data: MaskForm, user=Depends(get_verified_user)):
    config = await get_pii_config()
    if not config['enable']:
        return {'text': form_data.text, 'replacements': []}

    findings = await asyncio.to_thread(detect, form_data.text, config['categories'])
    excluded = set(form_data.exclude)
    selected = [f for idx, f in enumerate(findings) if idx not in excluded]
    text, replacements = mask(form_data.text, selected)
    return {'text': text, 'replacements': replacements}


@router.get('/config')
async def get_config(user=Depends(get_admin_user)):
    config = await get_pii_config()
    return {
        'ENABLE_PII_FILTER': config['enable'],
        'PII_FILTER_DEFAULT_MODE': config['default_mode'],
        'PII_FILTER_CATEGORIES': config['categories'],
        'AVAILABLE_CATEGORIES': CATEGORIES,
    }


@router.post('/config')
async def set_config(form_data: PiiConfigForm, user=Depends(get_admin_user)):
    await Config.upsert(
        {
            'pii.enable': form_data.ENABLE_PII_FILTER,
            'pii.default_mode': form_data.PII_FILTER_DEFAULT_MODE if form_data.PII_FILTER_DEFAULT_MODE in MODES else 'warn',
            'pii.categories': [c for c in form_data.PII_FILTER_CATEGORIES if c in CATEGORIES],
        }
    )
    return await get_config(user)
