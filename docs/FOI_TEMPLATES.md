# Freedom of Information request templates

The open data shows where EV taxi money went. It cannot show whether funded vehicles stayed in taxi use. These requests ask for **aggregate counts only**, so a public body can answer them without releasing personal data.

In Scotland, requests go under the Freedom of Information (Scotland) Act 2002. Public bodies should reply within 20 working days. If you are unhappy with the answer, you can ask for a review and then appeal to the Scottish Information Commissioner.

The Energy Saving Trust administers the loans on behalf of Transport Scotland, so send the funding requests to **Transport Scotland** (foi@transport.gov.scot).

---

## 1. Transport Scotland – Switched On Taxis and Hackney loan outcomes

> Under the Freedom of Information (Scotland) Act 2002, please provide, for each financial year from 2019/20 to 2025/26 and for each local authority area:
>
> 1. The number of loans issued under the Switched On Taxis loan and the Hackney (taxi) loan.
> 2. The number of those loans that were repaid early, and the number that were recalled or terminated because a condition of the loan was not met (for example, the vehicle ceasing to be used as a licensed taxi or private hire car).
> 3. Any condition requiring the vehicle to remain licensed as a taxi or private hire car, and for how long.
> 4. What checks are carried out, and how often, to confirm that funded vehicles remain licensed during the loan term.
> 5. Any internal audit or assurance reports on these loan streams produced since 2019.
>
> I am asking only for counts and documents, not for information about any individual borrower. Counts below five may be suppressed.

## 2. Each council licensing team – EV taxis and licence surrenders

> Under the Freedom of Information (Scotland) Act 2002, please provide, for each year from 2021 to 2025:
>
> 1. The number of licensed taxis and the number of licensed private hire cars, split by fuel type (battery electric, plug-in hybrid, other), at 31 March.
> 2. The number of battery-electric vehicles whose taxi or private hire vehicle licence was surrendered, or not renewed, within 24 months of first being licensed.
> 3. Whether the council records if a vehicle was purchased with public funding (for example a Switched On Taxis loan) when licensing it.
>
> Counts below five may be suppressed.

## 3. Transport Scotland – Plug-in Taxi Grant (UK government, via dealers)

> Please confirm whether Transport Scotland holds any figures on the number of UK Plug-in Taxi Grant claims for vehicles first registered in Scotland, by year since 2017. If not held, please advise which body holds it (I understand it may be the Office for Zero Emission Vehicles or the Department for Transport).

## 4. Department for Transport / OZEV – Plug-in Taxi Grant by nation

> Under the Freedom of Information Act 2000, please provide the number of Plug-in Taxi Grant claims and the total grant value by year since 2017, for vehicles registered to keepers in Scotland. Please also say whether OZEV checks that grant-funded vehicles remain in taxi use, and for how long.

---

### After the replies arrive

Add each answer as a CSV in `data/raw/` named `foi_<reference>_<topic>.csv`, and extend `scripts/build_dataset.py`. The most useful new indicator is:

**early-exit rate** = loans terminated or vehicles delicensed within 24 months ÷ loans issued, by council

That is the closest aggregate measure of the "fund as a taxi, then sell privately" pattern.
