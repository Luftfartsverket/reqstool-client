# Copyright © LFV

from dataclasses import dataclass, field

from reqstool.common.dataclasses.urn_id import UrnId


@dataclass(kw_only=True)
class TestStatisticsItem:
    nr_of_failed_tests: int = 0
    nr_of_missing_automated_tests: int = 0
    nr_of_missing_manual_tests: int = 0
    nr_of_skipped_tests: int = 0
    nr_of_passed_tests: int = 0
    nr_of_total_tests: int = 0
    not_applicable: bool = False

    def is_completed(self):
        if self.nr_of_missing_automated_tests or self.nr_of_missing_manual_tests > 0:
            return False
        return self.nr_of_total_tests == self.nr_of_passed_tests


@dataclass(kw_only=True, frozen=True)
class CombinedRequirementTestItem:
    completed: bool = field(default=bool)
    nr_of_implementations: int = field(default=int)
    automated_tests_stats: TestStatisticsItem = field(default_factory=TestStatisticsItem)
    mvrs_stats: TestStatisticsItem = field(default_factory=TestStatisticsItem)


@dataclass(kw_only=True)
class TotalStatisticsItem:
    nr_of_failed_tests: int = 0
    nr_of_missing_automated_tests: int = 0
    nr_of_missing_manual_tests: int = 0
    nr_of_skipped_tests: int = 0
    nr_of_passed_tests: int = 0
    nr_of_total_tests: int = 0
    nr_of_completed_requirements: int = 0
    nr_of_total_requirements: int = 0
    nr_of_reqs_with_implementation: int = 0
    nr_of_total_svcs: int = 0

    def update(self, completed: bool, combined_req_test_item: CombinedRequirementTestItem):
        self.nr_of_total_requirements += 1
        self.nr_of_missing_automated_tests += combined_req_test_item.automated_tests_stats.nr_of_missing_automated_tests
        self.nr_of_missing_manual_tests += combined_req_test_item.mvrs_stats.nr_of_missing_manual_tests
        self.nr_of_reqs_with_implementation += combined_req_test_item.nr_of_implementations

        if completed:
            self.nr_of_completed_requirements += 1


@dataclass(kw_only=True, frozen=True)
class StatisticsContainer:
    _requirement_statistics: dict[str, CombinedRequirementTestItem] = field(default_factory=lambda: {})

    _total_statistics: TotalStatisticsItem = field(default_factory=TotalStatisticsItem)

    def add_stats_for_requirement(
        self,
        req_urn_id: UrnId,
        impls: int,
        completed: bool,
        automated_tests_stats: TestStatisticsItem,
        mvrs_stats: TestStatisticsItem,
    ):
        assert id not in self._requirement_statistics

        combined_requirement_test_item = CombinedRequirementTestItem(
            completed=completed,
            nr_of_implementations=impls,
            automated_tests_stats=automated_tests_stats,
            mvrs_stats=mvrs_stats,
        )

        self._requirement_statistics[req_urn_id] = combined_requirement_test_item

        self._total_statistics.update(completed=completed, combined_req_test_item=combined_requirement_test_item)
