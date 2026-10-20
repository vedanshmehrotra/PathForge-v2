# PathForge Companion — Mozilla listing assets and fields

## Images

In the Developer Hub, choose **Images > Edit**. Upload `logo-128.png` as the add-on icon. Also supplied: `logo-64.png`, `logo-32.png`, `logo-512.png`, and the original high-resolution `logo-master.png`.

Use these actual extension UI captures as screenshots, preferably with the analysis image first:

| File | Suggested caption |
| --- | --- |
| `screenshot-02-analysis.png` | Example Python solution analysis with recognized patterns and related practice questions. Demo data. |
| `screenshot-03-practice.png` | Example matching wrong-answer feedback with pattern-focused practice suggestions. Demo data. |
| `screenshot-01-connect.png` | Connect your existing PathForge account from the sidebar. |

The logo is generated artwork based on the existing PathForge PF monogram and palette. The screenshots are captured from the real Firefox extension UI with controlled demo data; they are not AI-generated UI images or evidence of live LeetCode/production results.

## Fields to keep

- Name: **PathForge Companion**
- Add-on slug: **pathforge-companion**
- Summary and description: keep the values already entered.
- Experimental: keep checked for the initial release.
- Payment: keep unchecked if the required PathForge functionality remains free.
- Category: **Web Development**
- Support email: **mehrotravedansh2006@gmail.com** (public listing contact supplied by the developer)
- Support website: leave blank until a real support/help page exists. The main homepage can be set separately below.

## Additional Details

**Tags:** leetcode, python, algorithms, data structures, coding practice

**Contributions URL:** leave blank unless you have a donation page you want to link.

**Default Locale:** English (US)

**Homepage:** https://path-forge-v2.vercel.app/

## Technical Details

**Developer Comments** — public; paste this:

```text
Initial experimental release for desktop Firefox 142 and later. Currently supports Python/Python3 solutions.

Sign in on PathForge in the same browser window, connect your account in the sidebar, and open a LeetCode problem containing your solution. Use the recheck button after editing your code.

Correctness is shown only when a LeetCode submission matches the captured solution. Pattern analysis does not run your code or independently prove correctness. LeetCode editor changes may affect automatic code capture.

For support, email mehrotravedansh2006@gmail.com with your browser version, problem URL and a description of the issue. Do not include passwords or account tokens.
```

**UUID:** keep **pathforge-companion@pathforge.local**. Do not change the identifier for this submitted add-on.

**Whiteboard:** leave blank.

Developer Comments are public. Dedicated review-account access belongs only in the private Notes to Reviewer field.

These media uploads do not modify the packaged extension icons or require a code change. No website/backend or extension runtime source was changed for this asset task.

Reference: [Mozilla listing guidance](https://extensionworkshop.com/documentation/develop/create-an-appealing-listing/).
