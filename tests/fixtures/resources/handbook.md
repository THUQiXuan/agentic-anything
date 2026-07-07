# The Widget Handbook

An internal handbook about widget engineering.

## Widget Basics

A widget is a self-contained unit of cloud functionality. The standard
widget weighs 42 grams and ships in mint condition.

Widgets are versioned with semantic versioning. The current stable line
is the 3.x series.

## Deployment Guide

Deploy widgets with the `widgetctl deploy` command. The default region
is eu-west-1. Rollbacks complete in under 30 seconds.

Never deploy on Fridays without a canary.

## Pricing Model

The Starter tier costs $19 per month and includes 100 widgets.
The Team tier costs $79 per month and includes 1000 widgets.
Enterprise pricing is negotiated per contract.

## Troubleshooting

If a widget refuses to spin, check the flux alignment first.
Error code E42 means the widget cache is stale; run `widgetctl flush`.
