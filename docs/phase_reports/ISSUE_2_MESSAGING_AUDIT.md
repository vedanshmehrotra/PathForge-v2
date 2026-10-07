# Issue #2: Onboarding Messaging Audit & Fixes

**Status:** ✅ COMPLETE  
**Date:** 2026-06-19  
**Scope:** User-facing messaging only (no algorithm changes)

---

## Summary

Fixed 3 misleading messages in the onboarding flow that implied PathForge recommends based on user-selected topics. Updated messaging now accurately communicates that **selected topics are treated as existing strengths** and **PathForge focuses on weaker areas first**.

---

## Changes Made

### **Change #1: Landing Page - Step 1 Heading & Description**

**File:** `pathforge/templates/index.html` (lines 16-17)

#### **Before:**
```html
<h2 class="mt-2 font-semibold">Rate yourself</h2>
<p class="mt-2 text-sm text-zinc-400">Tell us which patterns you know. Your self-assessment sets your starting Elo.</p>
```

**Problem with this wording:**
- "Tell us which patterns you know" → implies the system will focus on those patterns
- "Your self-assessment sets your starting Elo" → doesn't explain the strategic purpose (finding weak spots)
- User expectation mismatch: "If I select Arrays, I'll practice Arrays"
- User reality: "If I select Arrays, I'll practice everything EXCEPT Arrays"

#### **After:**
```html
<h2 class="mt-2 font-semibold">Assess yourself</h2>
<p class="mt-2 text-sm text-zinc-400">Select areas where you're already strong. PathForge identifies your weaker areas and strengthens them first.</p>
```

**What changed:**
- "Rate yourself" → "Assess yourself" (clearer action)
- "Tell us which patterns you know" → "Select areas where you're already strong" (frames selection as strength assessment)
- Added explicit purpose: "PathForge identifies your weaker areas and strengthens them first" (sets correct expectation)

**User expectation after fix:**
- "If I select Arrays, PathForge will focus on my weak areas first, then return to Arrays"
- Accurate and prevents surprise

---

### **Change #2: Landing Page - Step 2 Description**

**File:** `pathforge/templates/index.html` (line 18)

#### **Before:**
```html
<p class="mt-2 text-sm text-zinc-400">Solve a recommended LeetCode problem targeting your weakest patterns.</p>
```

**Problem with this wording:**
- ✓ Correctly says "weakest patterns" but doesn't connect to the onboarding step
- User might think: "Oh, I'll practice what I selected" (because step 1 didn't clarify)
- Lacks context about why recommendations come from weak areas

#### **After:**
```html
<p class="mt-2 text-sm text-zinc-400">Solve a recommended LeetCode problem targeting your weaker patterns.</p>
```

**What changed:**
- "weakest patterns" → "weaker patterns" (softer language, less harsh, but still accurate)
- Minor wording improvement for consistency with Step 1's new message

**Why this wording:**
- Reinforces that recommendations target weak areas (not selected/strong areas)
- Works in conjunction with Step 1 to create clear mental model

---

### **Change #3: Registration Form - Checkbox Group Label**

**File:** `pathforge/templates/index.html` (new line 38, before line 39)

#### **Before:**
```html
<select class="field" name="experience_level">
  <!-- ... options ... -->
</select>
<div class="grid gap-2 text-sm text-zinc-300 sm:grid-cols-2">
  <label><input type="checkbox" name="confident_areas" value="arrays"> Arrays</label>
  <!-- ... more checkboxes ... -->
</div>
```

**Problem with this layout:**
- No label or instruction above checkboxes
- Users don't understand what selecting these topics means
- Critical context missing: "These are areas where you're strong"

#### **After:**
```html
<select class="field" name="experience_level">
  <!-- ... options ... -->
</select>
<p class="text-xs text-zinc-400">Select the areas where you're already strong:</p>
<div class="grid gap-2 text-sm text-zinc-300 sm:grid-cols-2">
  <label><input type="checkbox" name="confident_areas" value="arrays"> Arrays</label>
  <!-- ... more checkboxes ... -->
</div>
```

**What changed:**
- Added instructional text above checkboxes
- Clear, concise language: "Select the areas where you're already strong:"
- Uses small text style (text-xs) to avoid visual clutter
- Appears directly before checkboxes to create strong association

**User clarity after fix:**
- Unmistakable that checkboxes represent existing strengths
- Creates context before users interact with checkboxes
- Sets foundation for understanding Step 1 message

---

## Before/After Comparison

### **User Flow Context**

**Before (Confusing):**
```
Step 1 message: "Tell us which patterns you know"
              ↓ (ambiguous - could mean "practice these" or "these are my strengths")
User selects: Arrays, Binary Search, Greedy
              ↓ (user expects recommendations in these areas)
First recommendation: BFS (confusing - "I didn't select this!")
```

**After (Clear):**
```
Step 1 message: "Select areas where you're already strong. PathForge identifies your weaker areas and strengthens them first."
              ↓ (unambiguous - these are strengths, not practice targets)
Checkbox label: "Select the areas where you're already strong:"
              ↓ (reinforces the message)
User selects: Arrays, Binary Search, Greedy (knowing these are starting strengths)
              ↓ (user expects recommendations in weak areas)
First recommendation: BFS (expected - "pathforge is strengthening my weak areas first")
```

---

## Impact Analysis

### **What Changed**
- ✅ User-facing messaging in 3 locations
- ✅ Clarity and accuracy of onboarding expectations
- ✅ Consistency across landing page and form

### **What Did NOT Change**
- ❌ NO algorithm changes
- ❌ NO database schema changes
- ❌ NO API responses
- ❌ NO recommendation logic
- ❌ NO Elo seeding logic
- ❌ NO topic rotation behavior
- ❌ NO recommendation ranking

### **Benefit**
Eliminates the "expectation mismatch" issue by setting correct user expectations upfront. Users now understand that:
1. Selected topics represent existing strengths (baseline Elo +150)
2. Recommendations will focus on weaker areas first
3. This is intentional and strategic, not a bug

### **Risk**
- ✅ ZERO - This is pure messaging clarification
- ❌ No breaking changes
- ❌ No user data affected
- ❌ No existing users impacted (only affects new registrations onward)

---

## Files Modified

| File | Lines | Type | Change |
|------|-------|------|--------|
| `pathforge/templates/index.html` | 17-18 | Messaging | Step 1 heading and description |
| `pathforge/templates/index.html` | 18 | Messaging | Step 2 description |
| `pathforge/templates/index.html` | 38 | Content | Added checkbox group instruction label |

---

## Testing

### **Verification Checklist**
- ✅ Landing page loads without errors
- ✅ Step 1 message clearly states "areas where you're already strong"
- ✅ Step 1 explicitly mentions "PathForge identifies your weaker areas"
- ✅ Step 2 mentions "weaker patterns"
- ✅ Checkbox group has instructional text above
- ✅ All form fields are still functional
- ✅ Registration flow still works

### **How to Test**
1. Open `/` in browser (landing page)
2. Verify Step 1 heading reads "Assess yourself"
3. Verify Step 1 description mentions "weaker areas"
4. Scroll to registration form
5. Verify text above checkboxes reads "Select the areas where you're already strong:"
6. Register a new user and verify you're redirected to `/practice`
7. Verify first recommendation comes from a non-selected topic (expected behavior)

---

## Messaging Integrity

### **Principle**
All user-facing text must accurately reflect system behavior.

### **Before Fix**
System behavior: "Recommend from weaker areas first"  
User messaging: "Tell us which patterns you know"  
❌ **MISMATCH**

### **After Fix**
System behavior: "Recommend from weaker areas first"  
User messaging: "Select areas where you're already strong. PathForge identifies your weaker areas and strengthens them first."  
✅ **MATCH**

---

## Conclusion

The onboarding messaging audit identified and corrected 3 instances of misleading text that created user expectation mismatch. All updates are messaging-only with zero impact on system behavior or architecture. Users registering after this change will have accurate expectations about how PathForge's recommendation system works.
