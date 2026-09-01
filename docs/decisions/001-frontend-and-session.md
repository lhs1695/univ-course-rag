# 001 前端与登录

状态：已拍板（2026-09-01）

## 决定

- 前端：**Vue 3 + Vite + Element Plus**（已锁，不再二选 Naive UI）。
- 登录：**HTTP-only Cookie + 服务端 session**。Session 正文放服务器（Postgres 一张 `sessions` 表即可），Cookie 只带随机 `session_id`，`Secure`/`SameSite` 按部署补。
- 前端不存 JWT、不把 access token 放 `localStorage`。

## 为什么

三角色页是 B/S 后台形态，Vue 够用。Token 扔给前端会变成 XSS 直接偷登录态；大创也没有必须无状态水平扩展的压力。

## 明确不做（第一期）

学校 CAS/OAuth、小程序、Next.js 全栈。
