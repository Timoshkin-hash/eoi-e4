from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_scenarios(config: dict, cpm: float | None = None, churn_multiplier: float = 1.0) -> pd.DataFrame:
    users = config['active_users']
    arpu = config['subscription_arpu_rub_month']
    cpm_value = config['cpm_rub'] if cpm is None else cpm
    cac = config['cac_rub']
    lifetime = config['lifetime_months']
    loads = np.array(config['load_levels_impressions_day'], dtype=float)
    churn = np.array(config['churn_rates'], dtype=float) * churn_multiplier
    watch = np.array(config['watch_time_minutes'], dtype=float)
    churn = np.clip(churn, 0, 1)
    advertising = users * loads * 30 * cpm_value / 1000
    retained_users = users * (1 - churn)
    subscription = retained_users * arpu
    churned_users = users * churn
    churn_loss = churned_users * cac + churned_users * arpu * lifetime
    profit = advertising + subscription - churn_loss
    return pd.DataFrame({
        'Нагрузка, показов/день': loads.astype(int), 'Отток, %': churn * 100,
        'Время просмотра, мин': watch, 'Сохранившиеся пользователи': retained_users,
        'Доход рекламы, руб.': advertising, 'Доход подписки, руб.': subscription,
        'Потери оттока, руб.': churn_loss, 'Общая прибыль, руб.': profit,
    })


def best_scenario(df: pd.DataFrame) -> pd.Series:
    return df.loc[df['Общая прибыль, руб.'].idxmax()]


def format_rub(value: float, decimals: int = 0) -> str:
    return f'{value:,.{decimals}f}'.replace(',', ' ').replace('.', ',')


def format_mln(value: float, decimals: int = 1) -> str:
    return format_rub(value / 1_000_000, decimals)


def teacher_reference(config: dict) -> pd.DataFrame:
    ref = config['teacher_reference']
    return pd.DataFrame({'Нагрузка, показов/день': ref['load_levels_impressions_day'], 'Доход рекламы, млн руб.': ref['advertising_revenue_mln'], 'Доход подписки, млн руб.': ref['subscription_revenue_mln'], 'Потери оттока, млн руб.': ref['churn_loss_mln'], 'Общая прибыль, млн руб.': ref['total_profit_mln']})


def sensitivity_cpm(config: dict) -> pd.DataFrame:
    rows = []
    for cpm in config['sensitivity_cpm_rub']:
        best = best_scenario(calculate_scenarios(config, cpm=cpm))
        rows.append({'CPM, руб.': cpm, 'Оптимальная нагрузка': int(best['Нагрузка, показов/день']), 'Максимальная прибыль, млн руб.': best['Общая прибыль, руб.'] / 1_000_000})
    return pd.DataFrame(rows)


def sensitivity_churn(config: dict) -> pd.DataFrame:
    rows = []
    for load in config['load_levels_impressions_day']:
        values = {'Нагрузка, показов/день': load}
        for label, multiplier in [('−20%', 0.8), ('База', 1.0), ('+20%', 1.2)]:
            df = calculate_scenarios(config, churn_multiplier=multiplier)
            idx = df.index[df['Нагрузка, показов/день'] == load][0]
            values[f'Прибыль, млн руб. ({label})'] = df.loc[idx, 'Общая прибыль, руб.'] / 1_000_000
        rows.append(values)
    return pd.DataFrame(rows)
