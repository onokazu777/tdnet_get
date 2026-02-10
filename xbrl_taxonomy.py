# -*- coding: utf-8 -*-
"""
XBRLタクソノミ共有モジュール

TDnet XBRL で使用される要素名と日本語ラベルのマッピング、
およびTDnetサマリー独自要素の標準要素名への変換マップを提供する。

【使い方】
  from xbrl_taxonomy import XBRL_LABEL_MAP, TSE_ELEMENT_MAP

  # 要素名 → 日本語ラベル
  label = XBRL_LABEL_MAP.get("CashAndDeposits", "")   # → "現金及び預金"

  # TDnetサマリー独自名 → 標準要素名
  std = TSE_ELEMENT_MAP.get("SalesIFRS", "SalesIFRS")  # → "NetSales"

【参考】
  TDnetSearch タクソノミ一覧: https://tdnet-search.appspot.com/about
"""

# ============================================================
# XBRLラベルマッピング（要素名 → 日本語名称）
#
# Phase 1: 約160要素（主要な BS/PL/CF 詳細科目をカバー）
# ============================================================

XBRL_LABEL_MAP = {
    # ==========================================================
    # 損益計算書 (P/L) — 基本項目
    # ==========================================================
    "NetSales": "売上高",
    "Revenue": "売上収益（IFRS）",
    "OperatingRevenue1": "営業収益",
    "CostOfSales": "売上原価",
    "GrossProfit": "売上総利益",
    "SellingGeneralAndAdministrativeExpenses": "販売費及び一般管理費",
    "OperatingIncome": "営業利益",
    "NonOperatingIncome": "営業外収益",
    "NonOperatingExpenses": "営業外費用",
    "OrdinaryIncome": "経常利益",
    "ExtraordinaryIncome": "特別利益",
    "ExtraordinaryLoss": "特別損失",
    "IncomeBeforeIncomeTaxes": "税引前当期純利益",
    "IncomeTaxes": "法人税等合計",
    "IncomeTaxesCurrent": "法人税、住民税及び事業税",
    "IncomeTaxesDeferred": "法人税等調整額",
    "ProfitLoss": "当期純利益",
    "ProfitLossAttributableToOwnersOfParent": "親会社株主に帰属する当期純利益",
    "ProfitLossAttributableToNonControllingInterests": "非支配株主に帰属する当期純利益",
    "ComprehensiveIncome": "包括利益",
    "ComprehensiveIncomeAttributableToOwnersOfParent": "親会社株主に係る包括利益",
    "ComprehensiveIncomeAttributableToNonControllingInterests": "非支配株主に係る包括利益",

    # --- P/L 販管費内訳 ---
    "DepreciationSGA": "減価償却費（販管費）",
    "ResearchAndDevelopmentExpensesSGA": "研究開発費",
    "AdvertisingExpensesSGA": "広告宣伝費",
    "SalariesAndAllowancesSGA": "給料及び手当",
    "PersonalExpensesSGA": "人件費",
    "ProvisionForBonusesSGA": "賞与引当金繰入額（販管費）",
    "RetirementBenefitExpensesSGA": "退職給付費用（販管費）",
    "ProvisionOfAllowanceForDoubtfulAccountsSGA": "貸倒引当金繰入額（販管費）",
    "CommissionFeeSGA": "支払手数料（販管費）",
    "RentExpensesSGA": "賃借料（販管費）",
    "SubcontractExpensesSGA": "外注費（販管費）",

    # --- P/L 営業外収益 ---
    "InterestIncomeNOI": "受取利息",
    "DividendsIncomeNOI": "受取配当金",
    "InterestAndDividendsIncomeNOI": "受取利息及び配当金",
    "EquityInEarningsOfAffiliatesNOI": "持分法による投資利益",
    "ForeignExchangeGainsNOI": "為替差益",
    "RentIncomeNOI": "受取賃貸料",
    "MiscellaneousIncomeNOI": "雑収入",

    # --- P/L 営業外費用 ---
    "InterestExpensesNOE": "支払利息",
    "InterestOnBondsNOE": "社債利息",
    "EquityInLossesOfAffiliatesNOE": "持分法による投資損失",
    "ForeignExchangeLossesNOE": "為替差損",
    "MiscellaneousLossNOE": "雑損失",

    # --- P/L 特別利益 ---
    "GainOnSalesOfNoncurrentAssetsEI": "固定資産売却益",
    "GainOnSalesOfInvestmentSecuritiesEI": "投資有価証券売却益",
    "GainOnNegativeGoodwillEI": "負ののれん発生益",
    "GainOnSalesOfSubsidiariesStocksEI": "子会社株式売却益",
    "ReversalOfProvisionForDirectorsRetirementBenefitsEI": "役員退職慰労引当金戻入額",

    # --- P/L 特別損失 ---
    "LossOnSalesOfNoncurrentAssetsEL": "固定資産売却損",
    "LossOnRetirementOfNoncurrentAssetsEL": "固定資産除却損",
    "LossOnSalesAndRetirementOfNoncurrentAssetsEL": "固定資産除売却損",
    "ImpairmentLossEL": "減損損失",
    "LossOnSalesOfInvestmentSecuritiesEL": "投資有価証券売却損",
    "LossOnValuationOfInvestmentSecuritiesEL": "投資有価証券評価損",
    "LossOnValuationOfStocksOfSubsidiariesAndAffiliatesEL": "関係会社株式評価損",
    "SpecialRetirementExpensesEL": "特別退職金",
    "BusinessStructureImprovementExpensesEL": "事業構造改善費用",
    "LossOnDisasterEL": "災害による損失",

    # ==========================================================
    # 貸借対照表 (B/S) — 流動資産
    # ==========================================================
    "CurrentAssets": "流動資産合計",
    "CashAndDeposits": "現金及び預金",
    "NotesAndAccountsReceivableTrade": "受取手形及び売掛金",
    "NotesReceivableTrade": "受取手形",
    "AccountsReceivableTrade": "売掛金",
    "ElectronicallyRecordedMonetaryClaimsOperatingCA": "電子記録債権",
    "ShortTermInvestmentSecurities": "有価証券（流動）",
    "Inventories": "たな卸資産",
    "Merchandise": "商品",
    "FinishedGoods": "製品",
    "MerchandiseAndFinishedGoods": "商品及び製品",
    "SemiFinishedGoods": "半製品",
    "WorkInProcess": "仕掛品",
    "RawMaterials": "原材料",
    "RawMaterialsAndSupplies": "原材料及び貯蔵品",
    "Supplies": "貯蔵品",
    "RealEstateForSale": "販売用不動産",
    "DeferredTaxAssetsCA": "繰延税金資産（流動）",
    "OtherCA": "その他（流動資産）",
    "AllowanceForDoubtfulAccountsCA": "貸倒引当金（流動）",

    # --- B/S 有形固定資産 ---
    "NoncurrentAssets": "固定資産合計",
    "PropertyPlantAndEquipment": "有形固定資産",
    "Buildings": "建物",
    "BuildingsNet": "建物（純額）",
    "BuildingsAndStructures": "建物及び構築物",
    "BuildingsAndStructuresNet": "建物及び構築物（純額）",
    "Structures": "構築物",
    "StructuresNet": "構築物（純額）",
    "MachineryAndEquipment": "機械及び装置",
    "MachineryAndEquipmentNet": "機械及び装置（純額）",
    "MachineryEquipmentAndVehicles": "機械装置及び運搬具",
    "MachineryEquipmentAndVehiclesNet": "機械装置及び運搬具（純額）",
    "ToolsFurnitureAndFixtures": "工具、器具及び備品",
    "ToolsFurnitureAndFixturesNet": "工具、器具及び備品（純額）",
    "Land": "土地",
    "LeaseAssetsNetPPE": "リース資産（純額）",
    "ConstructionInProgress": "建設仮勘定",
    "OtherNetPPE": "その他（有形固定資産）",

    # --- B/S 無形固定資産 ---
    "IntangibleAssets": "無形固定資産",
    "Goodwill": "のれん",
    "Software": "ソフトウエア",
    "SoftwareInProgress": "ソフトウエア仮勘定",
    "OtherIA": "その他（無形固定資産）",

    # --- B/S 投資その他の資産 ---
    "InvestmentsAndOtherAssets": "投資その他の資産",
    "InvestmentSecurities": "投資有価証券",
    "StocksOfSubsidiariesAndAffiliates": "関係会社株式",
    "LongTermLoansReceivable": "長期貸付金",
    "LongTermLoansReceivableFromSubsidiariesAndAffiliates": "関係会社長期貸付金",
    "DeferredTaxAssetsIOA": "繰延税金資産（固定）",
    "NetDefinedBenefitAsset": "退職給付に係る資産",
    "GuaranteeDepositsIOA": "差入保証金（投資）",
    "OtherIOA": "その他（投資その他の資産）",
    "AllowanceForDoubtfulAccountsIOAByGroup": "貸倒引当金（投資）",
    "DeferredAssets": "繰延資産",
    "TotalAssets": "総資産",
    "Assets": "資産合計",

    # --- B/S 流動負債 ---
    "CurrentLiabilities": "流動負債合計",
    "NotesAndAccountsPayableTrade": "支払手形及び買掛金",
    "NotesPayableTrade": "支払手形",
    "AccountsPayableTrade": "買掛金",
    "ElectronicallyRecordedObligationsOperatingCL": "電子記録債務",
    "ShortTermLoansPayable": "短期借入金",
    "CurrentPortionOfLongTermLoansPayable": "1年内返済予定の長期借入金",
    "CurrentPortionOfBonds": "1年内償還予定の社債",
    "AccountsPayableOther": "未払金",
    "AccruedExpenses": "未払費用",
    "IncomeTaxesPayable": "未払法人税等",
    "AdvancesReceived": "前受金",
    "ProvisionForBonuses": "賞与引当金",
    "ProvisionForDirectorsBonuses": "役員賞与引当金",
    "LeaseObligationsCL": "リース債務（流動）",
    "OtherCL": "その他（流動負債）",

    # --- B/S 固定負債 ---
    "NoncurrentLiabilities": "固定負債合計",
    "BondsPayable": "社債",
    "LongTermLoansPayable": "長期借入金",
    "DeferredTaxLiabilitiesNCL": "繰延税金負債",
    "ProvisionForRetirementBenefits": "退職給付引当金",
    "NetDefinedBenefitLiability": "退職給付に係る負債",
    "ProvisionForDirectorsRetirementBenefits": "役員退職慰労引当金",
    "LeaseObligationsNCL": "リース債務（固定）",
    "AssetRetirementObligationsNCL": "資産除去債務",
    "OtherNCL": "その他（固定負債）",
    "TotalLiabilities": "負債合計",
    "Liabilities": "負債合計",

    # --- B/S 純資産 ---
    "NetAssets": "純資産合計",
    "ShareholdersEquity": "株主資本合計",
    "CapitalStock": "資本金",
    "CapitalSurplus": "資本剰余金",
    "LegalCapitalSurplus": "資本準備金",
    "OtherCapitalSurplus": "その他資本剰余金",
    "RetainedEarnings": "利益剰余金",
    "LegalRetainedEarnings": "利益準備金",
    "OtherRetainedEarnings": "その他利益剰余金",
    "GeneralReserve": "別途積立金",
    "RetainedEarningsBroughtForward": "繰越利益剰余金",
    "TreasuryStock": "自己株式",
    "ValuationAndTranslationAdjustments": "評価・換算差額等",
    "ValuationDifferenceOnAvailableForSaleSecurities": "その他有価証券評価差額金",
    "DeferredGainsOrLossesOnHedges": "繰延ヘッジ損益",
    "RevaluationReserveForLand": "土地再評価差額金",
    "ForeignCurrencyTranslationAdjustment": "為替換算調整勘定",
    "RemeasurementsOfDefinedBenefitPlans": "退職給付に係る調整累計額",
    "SubscriptionRightsToShares": "新株予約権",
    "NonControllingInterests": "非支配株主持分",

    # ==========================================================
    # キャッシュフロー計算書 (CF)
    # ==========================================================
    "NetCashProvidedByUsedInOperatingActivities": "営業活動によるCF",
    "NetCashProvidedByUsedInInvestingActivities": "投資活動によるCF",
    "NetCashProvidedByUsedInFinancingActivities": "財務活動によるCF",
    "CashAndCashEquivalents": "現金及び現金同等物期末残高",
    "IncreaseDecreaseInCashAndCashEquivalents": "現金及び現金同等物の増減額",

    # --- CF 営業活動の内訳 ---
    "DepreciationAndAmortizationOpeCF": "減価償却費（CF）",
    "ImpairmentLossOpeCF": "減損損失（CF）",
    "AmortizationOfGoodwillOpeCF": "のれん償却額（CF）",
    "IncreaseDecreaseInAllowanceForDoubtfulAccountsOpeCF": "貸倒引当金の増減額",
    "InterestAndDividendsIncomeOpeCF": "受取利息及び受取配当金（CF）",
    "InterestExpensesOpeCF": "支払利息（CF）",
    "EquityInEarningsLossesOfAffiliatesOpeCF": "持分法による投資損益（CF）",
    "LossGainOnSalesOfPropertyPlantAndEquipmentOpeCF": "有形固定資産売却損益（CF）",
    "LossGainOnSalesOfInvestmentSecuritiesOpeCF": "投資有価証券売却損益（CF）",
    "DecreaseIncreaseInNotesAndAccountsReceivableTradeOpeCF": "売上債権の増減額",
    "DecreaseIncreaseInInventoriesOpeCF": "たな卸資産の増減額",
    "IncreaseDecreaseInNotesAndAccountsPayableTradeOpeCF": "仕入債務の増減額",
    "IncreaseDecreaseInProvisionForBonusesOpeCF": "賞与引当金の増減額",
    "IncreaseDecreaseInNetDefinedBenefitLiabilityOpeCF": "退職給付に係る負債の増減額",
    "IncreaseDecreaseInProvisionForRetirementBenefitsOpeCF": "退職給付引当金の増減額",
    "OtherNetOpeCF": "その他（営業CF）",
    "SubtotalOpeCF": "小計（営業CF）",
    "InterestAndDividendsIncomeReceivedOpeCFInvCF": "利息及び配当金の受取額",
    "InterestExpensesPaidOpeCFFinCF": "利息の支払額",
    "IncomeTaxesPaidOpeCF": "法人税等の支払額",

    # --- CF 投資活動の内訳 ---
    "PurchaseOfPropertyPlantAndEquipmentInvCF": "有形固定資産の取得による支出",
    "ProceedsFromSalesOfPropertyPlantAndEquipmentInvCF": "有形固定資産の売却による収入",
    "PurchaseOfIntangibleAssetsInvCF": "無形固定資産の取得による支出",
    "PurchaseOfInvestmentSecuritiesInvCF": "投資有価証券の取得による支出",
    "ProceedsFromSalesOfInvestmentSecuritiesInvCF": "投資有価証券の売却による収入",
    "ProceedsFromSalesAndRedemptionOfInvestmentSecuritiesInvCF": "投資有価証券の売却及び償還による収入",
    "PaymentsOfLoansReceivableInvCF": "貸付けによる支出",
    "CollectionOfLoansReceivableInvCF": "貸付金の回収による収入",
    "PurchaseOfInvestmentsInSubsidiariesResultingInChangeInScopeOfConsolidationInvCF": "連結範囲変更を伴う子会社株式の取得による支出",
    "OtherNetInvCF": "その他（投資CF）",

    # --- CF 財務活動の内訳 ---
    "NetIncreaseDecreaseInShortTermLoansPayableFinCF": "短期借入金の純増減額",
    "IncreaseInShortTermLoansPayableFinCF": "短期借入れによる収入",
    "DecreaseInShortTermLoansPayableFinCF": "短期借入金の返済による支出",
    "ProceedsFromLongTermLoansPayableFinCF": "長期借入れによる収入",
    "RepaymentOfLongTermLoansPayableFinCF": "長期借入金の返済による支出",
    "ProceedsFromIssuanceOfBondsFinCF": "社債の発行による収入",
    "RedemptionOfBondsFinCF": "社債の償還による支出",
    "ProceedsFromIssuanceOfCommonStockFinCF": "株式の発行による収入",
    "PurchaseOfTreasuryStockFinCF": "自己株式の取得による支出",
    "ProceedsFromDisposalOfTreasuryStockFinCF": "自己株式の処分による収入",
    "CashDividendsPaidFinCF": "配当金の支払額",
    "DividendsPaidToNonControllingInterestsFinCF": "非支配株主への配当金の支払額",
    "RepaymentsOfLeaseObligationsFinCF": "リース債務の返済による支出",
    "OtherNetFinCF": "その他（財務CF）",

    # --- CF 為替影響 ---
    "EffectOfExchangeRateChangeOnCashAndCashEquivalents": "現金及び現金同等物に係る換算差額",

    # ==========================================================
    # 1株当たり情報
    # ==========================================================
    "EarningsPerShare": "1株当たり当期純利益",
    "DilutedEarningsPerShare": "潜在株式調整後EPS",
    "DividendPerShare": "1株当たり配当額",
    "NetAssetsPerShare": "1株当たり純資産",

    # ==========================================================
    # 経営指標
    # ==========================================================
    "EquityToAssetRatio": "自己資本比率（%）",
    "RateOfReturnOnEquity": "自己資本利益率ROE（%）",
    "PriceEarningsRatio": "株価収益率PER（倍）",
    "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock": "期末発行済株式数",
    "NumberOfTreasuryStockAtTheEndOfFiscalYear": "期末自己株式数",
    "AverageNumberOfShares": "期中平均株式数",

    # ==========================================================
    # 営業収益・経常収益（業種別）
    # ==========================================================
    "OrdinaryRevenuesBK": "経常収益",
    "OrdinaryRevenuesIN": "経常収益（保険）",
    "ChangeInOrdinaryRevenuesBK": "経常収益増減率",
    "ChangeInOrdinaryRevenuesIN": "経常収益増減率（保険）",

    # ==========================================================
    # 会社情報 (DEI)
    # ==========================================================
    "FilerNameInJapaneseDEI": "提出者名",
    "SecurityCodeDEI": "証券コード",
    "AccountingStandardsDEI": "会計基準",
    "CurrentFiscalYearStartDateDEI": "当期開始日",
    "CurrentFiscalYearEndDateDEI": "当期終了日",
    "CurrentPeriodEndDateDEI": "当四半期末日",
    "TypeOfCurrentPeriodDEI": "当四半期会計期間の種類",
}


# ============================================================
# TDnetサマリー要素名 → 標準要素名マッピング
#
# TDnetの決算短信サマリーは tse-ed-t 名前空間独自の要素名を使う。
# このマップで標準要素名に変換し、XBRL_LABEL_MAP で日本語化する。
# ============================================================

TSE_ELEMENT_MAP = {
    # --- P/L 日本基準 ---
    "NetSales": "NetSales",
    "OperatingIncome": "OperatingIncome",
    "OrdinaryIncome": "OrdinaryIncome",
    "ProfitLoss": "ProfitLoss",
    "ProfitLossAttributableToOwnersOfParent": "ProfitLossAttributableToOwnersOfParent",
    "ComprehensiveIncome": "ComprehensiveIncome",
    # --- P/L IFRS ---
    "SalesIFRS": "NetSales",
    "RevenueIFRS": "NetSales",
    "OperatingIncomeIFRS": "OperatingIncome",
    "ProfitBeforeTaxIFRS": "IncomeBeforeIncomeTaxes",
    "ProfitLossIFRS": "ProfitLoss",
    "ProfitLossAttributableToOwnersOfParentIFRS": "ProfitLossAttributableToOwnersOfParent",
    "ComprehensiveIncomeIFRS": "ComprehensiveIncome",
    # --- 変動率 ---
    "ChangeInNetSales": "ChangeInNetSales",
    "ChangeInOperatingIncome": "ChangeInOperatingIncome",
    "ChangeInOrdinaryIncome": "ChangeInOrdinaryIncome",
    "ChangeInProfitLoss": "ChangeInProfitLoss",
    "ChangeInSalesIFRS": "ChangeInNetSales",
    "ChangeInOperatingIncomeIFRS": "ChangeInOperatingIncome",
    "ChangeInProfitBeforeTaxIFRS": "ChangeInIncomeBeforeTaxes",
    "ChangeInProfitLossIFRS": "ChangeInProfitLoss",
    # --- EPS ---
    "EarningsPerShare": "EarningsPerShare",
    "DilutedEarningsPerShare": "DilutedEarningsPerShare",
    "EarningsPerShareIFRS": "EarningsPerShare",
    "DilutedEarningsPerShareIFRS": "DilutedEarningsPerShare",
    # --- B/S ---
    "TotalAssets": "TotalAssets",
    "NetAssets": "NetAssets",
    "Equity": "ShareholdersEquity",
    "TotalAssetsIFRS": "TotalAssets",
    "NetAssetsIFRS": "NetAssets",
    "EquityIFRS": "ShareholdersEquity",
    "EquityToAssetRatio": "EquityToAssetRatio",
    "EquityToAssetRatioIFRS": "EquityToAssetRatio",
    "BookValuePerShare": "NetAssetsPerShare",
    "BookValuePerShareIFRS": "NetAssetsPerShare",
    # --- 配当 ---
    "DividendPerShare": "DividendPerShare",
    "AnnualDividendPerShare": "DividendPerShare",
    "DividendPerShareIFRS": "DividendPerShare",
    # --- CF ---
    "CashFlowsFromOperatingActivities": "NetCashProvidedByUsedInOperatingActivities",
    "CashFlowsFromInvestingActivities": "NetCashProvidedByUsedInInvestingActivities",
    "CashFlowsFromFinancingActivities": "NetCashProvidedByUsedInFinancingActivities",
    "CashAndEquivalents": "CashAndCashEquivalents",
    "CashFlowsFromOperatingActivitiesIFRS": "NetCashProvidedByUsedInOperatingActivities",
    "CashFlowsFromInvestingActivitiesIFRS": "NetCashProvidedByUsedInInvestingActivities",
    "CashFlowsFromFinancingActivitiesIFRS": "NetCashProvidedByUsedInFinancingActivities",
    "CashAndEquivalentsIFRS": "CashAndCashEquivalents",
    # --- IFRS追加要素 ---
    "ProfitIFRS": "ProfitLoss",
    "ProfitAttributableToOwnersOfParentIFRS": "ProfitLossAttributableToOwnersOfParent",
    "TotalComprehensiveIncomeIFRS": "ComprehensiveIncome",
    "BasicEarningsPerShareIFRS": "EarningsPerShare",
    "TotalEquityIFRS": "NetAssets",
    "EquityAttributableToOwnersOfParentIFRS": "ShareholdersEquity",
    "EquityAttributableToOwnersOfParentToTotalAssetsRatioIFRS": "EquityToAssetRatio",
    # --- 営業収益（運輸・物流・卸売等）---
    "OperatingRevenues": "OperatingRevenue1",
    "OperatingRevenuesIFRS": "OperatingRevenue1",
    "OperatingRevenuesSpecific": "OperatingRevenue1",
    "OperatingRevenuesSE": "OperatingRevenue1",
    "ChangeInOperatingRevenues": "ChangeInNetSales",
    "ChangeInOperatingRevenuesIFRS": "ChangeInNetSales",
    "ChangeInOperatingRevenuesSpecific": "ChangeInNetSales",
    "ChangeInOperatingRevenuesSE": "ChangeInNetSales",
    # --- IFRS売上高 ---
    "NetSalesIFRS": "NetSales",
    "ChangeInNetSalesIFRS": "ChangeInNetSales",
    # --- 米国基準 ---
    "NetSalesUS": "NetSales",
    "TotalRevenuesUS": "NetSales",
    "ChangeInNetSalesUS": "ChangeInNetSales",
    "ChangeInTotalRevenuesUS": "ChangeInNetSales",
    # --- 銀行業・保険業 ---
    "OrdinaryRevenuesBK": "OrdinaryRevenuesBK",
    "ChangeInOrdinaryRevenuesBK": "ChangeInOrdinaryRevenuesBK",
    "OrdinaryRevenuesIN": "OrdinaryRevenuesIN",
    "ChangeInOrdinaryRevenuesIN": "ChangeInOrdinaryRevenuesIN",
}


# ============================================================
# ユーティリティ関数
# ============================================================

def get_label(element_name: str, tse_map: bool = True) -> str:
    """
    XBRL要素名から日本語ラベルを取得する。

    Args:
        element_name: XBRL要素名（例: "CashAndDeposits"）
        tse_map: TDnetサマリー要素の変換を適用するか

    Returns:
        日本語ラベル（見つからない場合は空文字列）
    """
    if tse_map:
        mapped = TSE_ELEMENT_MAP.get(element_name, element_name)
        label = XBRL_LABEL_MAP.get(mapped, "")
        if label:
            return label
    return XBRL_LABEL_MAP.get(element_name, "")


def get_label_or_name(element_name: str, tse_map: bool = True) -> str:
    """
    XBRL要素名から日本語ラベルを取得する。
    ラベルが無い場合は要素名そのものを返す。
    """
    label = get_label(element_name, tse_map)
    return label if label else element_name
