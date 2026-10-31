## Per bench x model x effort x trial

| Bench | Model | Effort | Trial | n | success | outcomes | cost total $ | cost / success $ | cost p90 $ | cost max $ | turns mean | turns max | wall mean s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| browser_flow | claude-fable-5-1 | low | 1 | 11 | 10 | correct 10, wrong 1 | 24.91 | 2.4905 | 2.3675 | 2.4431 | 52.3 | 67 | 140.5 |
| browser_flow | claude-haiku-5-5 | low | 1 | 11 | 11 | correct 11 | 0.38 | 0.0346 | 0.0391 | 0.0423 | 47.5 | 57 | 91.3 |
| browser_flow | claude-haiku-5-5 | low | 2 | 11 | 11 | correct 11 | 0.38 | 0.0344 | 0.0374 | 0.0423 | 48.3 | 56 | 82.1 |
| browser_flow | claude-haiku-5-5 | low | 3 | 11 | 11 | correct 11 | 0.35 | 0.0321 | 0.0351 | 0.0362 | 45.0 | 59 | 83.2 |
| browser_flow | claude-sonnet-5-5 | low | 1 | 11 | 11 | correct 11 | 4.69 | 0.4268 | 0.4387 | 0.4554 | 40.7 | 47 | 76.3 |
| own_app_flow | claude-fable-5-1 | low | 1 | 15 | 14 | correct 14, incomplete 1 | 37.80 | 2.6997 | 2.6806 | 2.7184 | 41.1 | 46 | 209.4 |
| own_app_flow | claude-fable-5-1 | low | 2 | 1 | 1 | correct 1 | 3.03 | 3.0342 | 3.0342 | 3.0342 | 56.0 | 56 | 408.3 |
| own_app_flow | claude-haiku-5-5 | low | 1 | 15 | 14 | correct 14, incomplete 1 | 0.56 | 0.0401 | 0.0431 | 0.0469 | 42.5 | 51 | 112.1 |
| own_app_flow | claude-haiku-5-5 | low | 2 | 15 | 14 | correct 14, incomplete 1 | 0.56 | 0.0403 | 0.0428 | 0.0433 | 40.9 | 48 | 181.2 |
| own_app_flow | claude-sonnet-5-5 | low | 1 | 15 | 12 | correct 12, wrong 3 | 7.33 | 0.6106 | 0.5170 | 0.5230 | 43.3 | 50 | 123.6 |
| own_app_flow | claude-sonnet-5-5 | low | 2 | 15 | 13 | correct 13, incomplete 1, wrong 1 | 6.97 | 0.5358 | 0.4931 | 0.4973 | 38.7 | 43 | 139.3 |
| find_feature | claude-fable-5-1 | low | 1 | 72 | 72 | correct 72 | 41.61 | 0.5779 | 0.5978 | 0.6009 | 2.5 | 5 | 8.3 |
| find_feature | claude-haiku-5-5 | low | 1 | 72 | 70 | correct 70, wrong 2 | 0.47 | 0.0067 | 0.0070 | 0.0075 | 2.8 | 7 | 6.2 |
| find_feature | claude-haiku-5-5 | low | 2 | 72 | 72 | correct 72 | 0.29 | 0.0040 | 0.0068 | 0.0080 | 3.1 | 7 | 6.4 |
| find_feature | claude-haiku-5-5 | low | 3 | 72 | 72 | correct 72 | 0.23 | 0.0031 | 0.0064 | 0.0071 | 3.1 | 10 | 6.5 |
| find_feature | claude-haiku-5-5 | medium | 1 | 72 | 72 | correct 72 | 0.47 | 0.0065 | 0.0071 | 0.0092 | 3.2 | 7 | 6.8 |
| find_feature | claude-haiku-5-5 | medium | 2 | 72 | 70 | correct 70, wrong 2 | 0.29 | 0.0041 | 0.0068 | 0.0078 | 3.0 | 10 | 6.8 |
| find_feature | claude-haiku-5-5 | medium | 3 | 72 | 71 | correct 71, wrong 1 | 0.45 | 0.0063 | 0.0069 | 0.0079 | 2.9 | 5 | 6.6 |
| find_feature | claude-sonnet-5-5 | low | 1 | 72 | 72 | correct 72 | 8.58 | 0.1192 | 0.1236 | 0.1412 | 2.4 | 5 | 6.0 |
| find_feature | claude-sonnet-5-5 | low | 2 | 72 | 72 | correct 72 | 8.31 | 0.1154 | 0.1189 | 0.1265 | 2.3 | 6 | 6.3 |
| fix_bug | claude-fable-5-1 | low | 1 | 10 | 10 | fixed 10 | 7.48 | 0.7478 | 0.8910 | 1.0036 | 4.7 | 10 | 25.6 |
| fix_bug | claude-haiku-5-5 | low | 1 | 10 | 10 | fixed 10 | 0.12 | 0.0122 | 0.0151 | 0.0230 | 5.9 | 9 | 28.1 |
| fix_bug | claude-sonnet-5-5 | low | 1 | 10 | 10 | fixed 10 | 1.49 | 0.1494 | 0.1633 | 0.2080 | 4.6 | 9 | 12.1 |
| fix_bug_hard | claude-fable-5-1 | low | 1 | 21 | 16 | fixed 16, still-failing 5 | 18.03 | 1.1270 | 1.0428 | 1.0863 | 6.3 | 12 | 31.0 |
| fix_bug_hard | claude-fable-5-1 | low+kunit | 1 | 21 | 21 | fixed 21 | 18.59 | 0.8852 | 1.0501 | 1.0926 | 8.0 | 15 | 48.3 |
| fix_bug_hard | claude-haiku-5-5 | low | 1 | 21 | 16 | fixed 16, still-failing 5 | 0.25 | 0.0158 | 0.0171 | 0.0179 | 6.4 | 13 | 26.6 |
| fix_bug_hard | claude-haiku-5-5 | low+kunit | 1 | 21 | 21 | fixed 21 | 0.30 | 0.0144 | 0.0203 | 0.0232 | 9.2 | 17 | 46.9 |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | 21 | 14 | fixed 14, still-failing 7 | 3.59 | 0.2564 | 0.2062 | 0.2599 | 6.5 | 15 | 22.2 |
| fix_bug_hard | claude-sonnet-5-5 | low+kunit | 1 | 21 | 21 | fixed 21 | 4.14 | 0.1971 | 0.2192 | 0.2973 | 9.9 | 20 | 39.9 |
| write_tests | claude-fable-5-1 | low | 1 | 10 | 4 | catches-bug 4, compile-fail 1, fails-on-correct-code 5 | 18.31 | 4.5774 | 2.5126 | 3.4443 | 10.9 | 31 | 167.8 |
| write_tests | claude-fable-5-1 | low+kunit | 1 | 10 | 10 | catches-bug 10 | 15.08 | 1.5078 | 1.9413 | 2.2945 | 8.9 | 15 | 133.9 |
| write_tests | claude-haiku-5-5 | low | 1 | 10 | 5 | catches-bug 5, compile-fail 1, fails-on-correct-code 4 | 0.25 | 0.0490 | 0.0342 | 0.0444 | 7.0 | 11 | 93.5 |
| write_tests | claude-haiku-5-5 | low+kunit | 1 | 10 | 10 | catches-bug 10 | 0.25 | 0.0252 | 0.0303 | 0.0398 | 11.0 | 21 | 90.9 |
| write_tests | claude-sonnet-5-5 | low | 1 | 10 | 7 | catches-bug 7, compile-fail 1, fails-on-correct-code 2 | 2.59 | 0.3705 | 0.3220 | 0.3707 | 6.4 | 9 | 50.3 |
| write_tests | claude-sonnet-5-5 | low+kunit | 1 | 10 | 10 | catches-bug 10 | 2.87 | 0.2870 | 0.3812 | 0.3883 | 9.4 | 17 | 65.7 |

## find_feature per family

| Model | Effort | Trial | Family | n | correct | outcomes | cost / correct $ | turns mean | wall mean s |
|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5-1 | low | 1 | callers | 12 | 12 | correct 12 | 0.5916 | 4.2 | 8.8 |
| claude-fable-5-1 | low | 1 | dispatch | 12 | 12 | correct 12 | 0.5740 | 2.2 | 6.8 |
| claude-fable-5-1 | low | 1 | exists | 24 | 24 | correct 24 | 0.5731 | 2.3 | 8.6 |
| claude-fable-5-1 | low | 1 | fields | 12 | 12 | correct 12 | 0.5785 | 2.2 | 8.2 |
| claude-fable-5-1 | low | 1 | refs | 12 | 12 | correct 12 | 0.5772 | 2.0 | 9.0 |
| claude-haiku-5-5 | low | 1 | callers | 12 | 11 | correct 11, wrong 1 | 0.0072 | 3.9 | 6.3 |
| claude-haiku-5-5 | low | 1 | dispatch | 12 | 12 | correct 12 | 0.0066 | 2.7 | 5.9 |
| claude-haiku-5-5 | low | 1 | exists | 24 | 24 | correct 24 | 0.0065 | 2.5 | 6.4 |
| claude-haiku-5-5 | low | 1 | fields | 12 | 11 | correct 11, wrong 1 | 0.0071 | 2.3 | 5.7 |
| claude-haiku-5-5 | low | 1 | refs | 12 | 12 | correct 12 | 0.0065 | 2.9 | 6.7 |
| claude-haiku-5-5 | low | 2 | callers | 12 | 12 | correct 12 | 0.0034 | 4.7 | 6.5 |
| claude-haiku-5-5 | low | 2 | dispatch | 12 | 12 | correct 12 | 0.0041 | 2.8 | 6.8 |
| claude-haiku-5-5 | low | 2 | exists | 24 | 24 | correct 24 | 0.0040 | 2.9 | 6.9 |
| claude-haiku-5-5 | low | 2 | fields | 12 | 12 | correct 12 | 0.0059 | 2.2 | 5.4 |
| claude-haiku-5-5 | low | 2 | refs | 12 | 12 | correct 12 | 0.0027 | 3.2 | 6.3 |
| claude-haiku-5-5 | low | 3 | callers | 12 | 12 | correct 12 | 0.0026 | 4.6 | 6.5 |
| claude-haiku-5-5 | low | 3 | dispatch | 12 | 12 | correct 12 | 0.0035 | 2.3 | 6.2 |
| claude-haiku-5-5 | low | 3 | exists | 24 | 24 | correct 24 | 0.0027 | 2.7 | 6.9 |
| claude-haiku-5-5 | low | 3 | fields | 12 | 12 | correct 12 | 0.0039 | 2.2 | 5.2 |
| claude-haiku-5-5 | low | 3 | refs | 12 | 12 | correct 12 | 0.0034 | 3.9 | 7.1 |
| claude-haiku-5-5 | medium | 1 | callers | 12 | 12 | correct 12 | 0.0066 | 4.2 | 7.0 |
| claude-haiku-5-5 | medium | 1 | dispatch | 12 | 12 | correct 12 | 0.0064 | 2.7 | 6.0 |
| claude-haiku-5-5 | medium | 1 | exists | 24 | 24 | correct 24 | 0.0066 | 2.9 | 7.4 |
| claude-haiku-5-5 | medium | 1 | fields | 12 | 12 | correct 12 | 0.0065 | 2.3 | 5.6 |
| claude-haiku-5-5 | medium | 1 | refs | 12 | 12 | correct 12 | 0.0066 | 3.8 | 7.3 |
| claude-haiku-5-5 | medium | 2 | callers | 12 | 12 | correct 12 | 0.0023 | 3.1 | 7.0 |
| claude-haiku-5-5 | medium | 2 | dispatch | 12 | 12 | correct 12 | 0.0043 | 2.5 | 5.9 |
| claude-haiku-5-5 | medium | 2 | exists | 24 | 24 | correct 24 | 0.0048 | 2.9 | 7.5 |
| claude-haiku-5-5 | medium | 2 | fields | 12 | 12 | correct 12 | 0.0035 | 2.2 | 5.2 |
| claude-haiku-5-5 | medium | 2 | refs | 12 | 10 | correct 10, wrong 2 | 0.0051 | 4.6 | 7.7 |
| claude-haiku-5-5 | medium | 3 | callers | 12 | 12 | correct 12 | 0.0065 | 3.5 | 7.2 |
| claude-haiku-5-5 | medium | 3 | dispatch | 12 | 12 | correct 12 | 0.0064 | 2.6 | 6.6 |
| claude-haiku-5-5 | medium | 3 | exists | 24 | 24 | correct 24 | 0.0059 | 2.7 | 6.7 |
| claude-haiku-5-5 | medium | 3 | fields | 12 | 11 | correct 11, wrong 1 | 0.0070 | 2.4 | 5.6 |
| claude-haiku-5-5 | medium | 3 | refs | 12 | 12 | correct 12 | 0.0064 | 3.3 | 6.6 |
| claude-sonnet-5-5 | low | 1 | callers | 12 | 12 | correct 12 | 0.1189 | 2.2 | 6.0 |
| claude-sonnet-5-5 | low | 1 | dispatch | 12 | 12 | correct 12 | 0.1216 | 2.8 | 6.3 |
| claude-sonnet-5-5 | low | 1 | exists | 24 | 24 | correct 24 | 0.1177 | 2.4 | 5.7 |
| claude-sonnet-5-5 | low | 1 | fields | 12 | 12 | correct 12 | 0.1187 | 2.2 | 5.9 |
| claude-sonnet-5-5 | low | 1 | refs | 12 | 12 | correct 12 | 0.1204 | 2.4 | 6.3 |
| claude-sonnet-5-5 | low | 2 | callers | 12 | 12 | correct 12 | 0.1163 | 2.8 | 6.3 |
| claude-sonnet-5-5 | low | 2 | dispatch | 12 | 12 | correct 12 | 0.1156 | 2.3 | 6.4 |
| claude-sonnet-5-5 | low | 2 | exists | 24 | 24 | correct 24 | 0.1146 | 2.3 | 6.3 |
| claude-sonnet-5-5 | low | 2 | fields | 12 | 12 | correct 12 | 0.1158 | 2.2 | 6.1 |
| claude-sonnet-5-5 | low | 2 | refs | 12 | 12 | correct 12 | 0.1153 | 2.1 | 6.1 |

## Every non-success response

| Bench | Model | Effort | Trial | Task | Outcome | Detail |
|---|---|---|---|---|---|---|
| browser_flow | claude-fable-5-1 | low | 1 | flow-09-edit-loses-name | wrong | items 7:pass (truth fails ['6', '7']) drove=full |
| own_app_flow | claude-fable-5-1 | low | 1 | store-10-update-ignored | incomplete | items 3:fail,4:fail,5:fail,6:fail,9:fail (truth fails ['7', '8', '10']) drove=none |
| own_app_flow | claude-haiku-5-5 | low | 1 | store-04-add-ignores-quantity | incomplete | items 4:not_run,5:not_run,6:not_run,7:not_run,8:not_run,9:not_run,10:not_run (truth fails ['3', '4', '5', '6']) drove=pa |
| own_app_flow | claude-haiku-5-5 | low | 2 | store-14-cancel-no-status | incomplete | items 8:fail (truth fails ['9', '10']) drove=partial |
| own_app_flow | claude-sonnet-5-5 | low | 1 | store-06-subtotal-skips-last | wrong | items 5:fail (truth fails ['6', '7']) drove=full |
| own_app_flow | claude-sonnet-5-5 | low | 1 | store-11-payment-method-ignored | wrong | items 9:fail (truth fails ['8']) drove=full |
| own_app_flow | claude-sonnet-5-5 | low | 1 | store-12-order-tax-doubled | wrong | items 9:fail (truth fails ['8', '10']) drove=full |
| own_app_flow | claude-sonnet-5-5 | low | 2 | store-05-cart-shows-cost-price | incomplete | items 1:fail,2:fail,3:fail,4:fail,8:fail,9:fail,10:fail (truth fails ['5', '6', '7']) drove=none |
| own_app_flow | claude-sonnet-5-5 | low | 2 | store-10-update-ignored | wrong | items 9:fail (truth fails ['7', '8', '10']) drove=full |
| find_feature | claude-haiku-5-5 | low | 1 | fields-06 | wrong |  |
| find_feature | claude-haiku-5-5 | low | 1 | callers-10 | wrong | lexical-confusion: lib/string_helpers.c has only definition |
| find_feature | claude-haiku-5-5 | medium | 2 | refs-05 | wrong |  |
| find_feature | claude-haiku-5-5 | medium | 2 | refs-10 | wrong |  |
| find_feature | claude-haiku-5-5 | medium | 3 | fields-06 | wrong |  |
| fix_bug_hard | claude-fable-5-1 | low | 1 | hard-multi-cmdline-01-get_option+get_options | still-failing |  |
| fix_bug_hard | claude-fable-5-1 | low | 1 | hard-multi-cmdline-03-get_option+_parse_integer_fixup_radix | still-failing |  |
| fix_bug_hard | claude-fable-5-1 | low | 1 | hard-multi-cmdline-04-get_option+_parse_integer_limit | still-failing |  |
| fix_bug_hard | claude-fable-5-1 | low | 1 | hard-multi-string_helpers-02-string_escape_mem+string_unescape | still-failing |  |
| fix_bug_hard | claude-fable-5-1 | low | 1 | hard-multi-string-01-strncasecmp+strcspn | still-failing |  |
| fix_bug_hard | claude-haiku-5-5 | low | 1 | hard-multi-cmdline-02-get_option+get_range | still-failing |  |
| fix_bug_hard | claude-haiku-5-5 | low | 1 | hard-multi-cmdline-03-get_option+_parse_integer_fixup_radix | still-failing |  |
| fix_bug_hard | claude-haiku-5-5 | low | 1 | hard-multi-cmdline-04-get_option+_parse_integer_limit | still-failing |  |
| fix_bug_hard | claude-haiku-5-5 | low | 1 | hard-multi-string_helpers-02-string_escape_mem+string_unescape | still-failing |  |
| fix_bug_hard | claude-haiku-5-5 | low | 1 | hard-multi-string-01-strncasecmp+strcspn | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-cmdline-01-get_option+get_options | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-cmdline-02-get_option+get_range | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-cmdline-03-get_option+_parse_integer_fixup_radix | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-cmdline-04-get_option+_parse_integer_limit | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-string_helpers-02-string_escape_mem+string_unescape | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-string_helpers-03-string_get_size+string_unescape | still-failing |  |
| fix_bug_hard | claude-sonnet-5-5 | low | 1 | hard-multi-string-01-strncasecmp+strcspn | still-failing |  |
| write_tests | claude-fable-5-1 | low | 1 | test-string-01-strncasecmp | fails-on-correct-code | cases=19 clean_fail=2 bug_fail=12 detects=True |
| write_tests | claude-fable-5-1 | low | 1 | test-string_helpers-02-string_escape_mem | fails-on-correct-code | cases=26 clean_fail=1 bug_fail=21 detects=True |
| write_tests | claude-fable-5-1 | low | 1 | test-string_helpers-03-string_unescape | fails-on-correct-code | cases=18 clean_fail=1 bug_fail=15 detects=True |
| write_tests | claude-fable-5-1 | low | 1 | test-cmdline-01-get_option | compile-fail | $KERNEL_WT/grade-tests/include/kunit/test.h:774:39: error: inval |
| write_tests | claude-fable-5-1 | low | 1 | test-cmdline-02-get_options | fails-on-correct-code | cases=41 clean_fail=2 bug_fail=30 detects=True |
| write_tests | claude-fable-5-1 | low | 1 | test-cmdline-03-memparse | fails-on-correct-code | cases=22 clean_fail=1 bug_fail=0 detects=False |
| write_tests | claude-haiku-5-5 | low | 1 | test-string-01-strncasecmp | fails-on-correct-code | cases=14 clean_fail=2 bug_fail=11 detects=True |
| write_tests | claude-haiku-5-5 | low | 1 | test-string-02-strcspn | fails-on-correct-code | cases=16 clean_fail=1 bug_fail=13 detects=True |
| write_tests | claude-haiku-5-5 | low | 1 | test-string_helpers-02-string_escape_mem | fails-on-correct-code | cases=20 clean_fail=1 bug_fail=15 detects=True |
| write_tests | claude-haiku-5-5 | low | 1 | test-string_helpers-03-string_unescape | fails-on-correct-code | cases=15 clean_fail=2 bug_fail=12 detects=True |
| write_tests | claude-haiku-5-5 | low | 1 | test-cmdline-01-get_option | compile-fail | $KERNEL_WT/grade-tests/include/kunit/test.h:774:39: error: inval |
| write_tests | claude-sonnet-5-5 | low | 1 | test-string_helpers-01-string_get_size | fails-on-correct-code | cases=11 clean_fail=2 bug_fail=5 detects=True |
| write_tests | claude-sonnet-5-5 | low | 1 | test-string_helpers-02-string_escape_mem | fails-on-correct-code | cases=20 clean_fail=1 bug_fail=16 detects=True |
| write_tests | claude-sonnet-5-5 | low | 1 | test-cmdline-01-get_option | compile-fail | $KERNEL_WT/grade-tests/include/kunit/test.h:774:39: error: inval |
