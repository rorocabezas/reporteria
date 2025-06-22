# -*- coding: utf-8 -*-
# pages/utils.py
import streamlit as st
import pandas as pd

def format_currency(value):
    return "${:,.0f}".format(value)

def format_percentage(value):
    return "{:.2f}%".format(value)

def format_number(value, decimals=2):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_variacion(df, columna_actual, columna_anterior):
    df = df.fillna(0)
    zero_mask = (df[columna_actual] == 0) | (df[columna_anterior] == 0)
    variacion = df.apply(lambda row: 0 if zero_mask[row.name] else ((row[columna_actual] / row[columna_anterior]) - 1) * 100, axis=1)
    variacion = variacion.apply(lambda x: f"{x:.2f}%" if x >= 0 else f"{x:.2f}%")
    return variacion

def calcular_ticket_promedio(df, columna_ingresos, columna_tickets):
    df = df.fillna(0)
    zero_mask = (df[columna_ingresos] == 0) | (df[columna_tickets] == 0)
    ticket_promedio = df.apply(lambda row: 0 if zero_mask[row.name] else int(row[columna_ingresos] / row[columna_tickets]), axis=1)
    return ticket_promedio

# Variaciones Totales
def calcular_variacion_total(df, columna_actual, columna_anterior):
    total_actual = df[columna_actual].sum()
    total_anterior = df[columna_anterior].sum()
    variacion = (total_actual / total_anterior - 1) * 100
    return f"{variacion:.2f}%"

def calcular_ticket_total(df, columna_ingresos, columna_ticket):
    total_actual = df[columna_ingresos].sum()
    total_ticket = df[columna_ticket].sum()
    ticket_prom = (total_actual / total_ticket)
    return round(ticket_prom)