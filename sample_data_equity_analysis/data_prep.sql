/*
 * SPDX-License-Identifier: Apache-2.0
 * Licensed to the Ed-Fi Alliance under one or more agreements.
 * The Ed-Fi Alliance licenses this file to you under the Apache License, Version 2.0.
 * See the LICENSE and NOTICES files in the project root for more information.
 */

/*
Goal: ensure there is no obvious demographic skewing in the data.

Data to evaluate:
  - Grade
  - Assessment scores
  - Attendance
  - Discipline incidents

Cross reference:
  - Disability
  - Language
  - Language Use
  - Program Participation: Foodservice
  - Program Participation: 504
  - Race
  - Student Characteristic
  - Tribal Affiliation
  - Sex/Gender
  - Hispanic ethnicity
  - Limited English proficiency

Approach:
  - Use AMT views where possible to simplify queries.
  - Run separate two sets of queries: one using a student's relationship with the
    school, and another using the relationship with the local education agency.
  - These queries must account for the fact that a student could have multiple
    relationships, for example could be connected to two different schools.
    Furthermore, they could have separate demographics at these different schools.
*/

/*
.\EdFi.AnalyticsMiddleTier.Console.exe --connectionstring "server=localhost;database=EdFi_Ods_Populated_Template;trusted_connection=yes" --options equity
*/

--
-- Special note: Ed-Fi sample data does not have any program associations, therefore no need to
-- incorporate into the queries below. Als no disability
--
-- select * from edfi.StudentEducationOrganizationAssociationProgramParticipation
-- select * from edfi.StudentEducationOrganizationAssociationTribalAffiliation
-- select count(1) from edfi.StudentEducationOrganizationAssociationDisability


--
---- Begin with Local Education Agency relationship
--

-- Start over...
-- DROP TABLE edfi_dei.leaStudents

create table edfi_dei.leaStudents (
    LocalEducationAgencyKey VARCHAR(1000),
    StudentLocalEducationAgencyKey VARCHAR(1000),
    StudentKey VARCHAR(1000),
    LimitedEnglishProficiency VARCHAR(3) DEFAULT (''),
    IsHispanic VARCHAR(3) DEFAULT (''),
    Sex VARCHAR(1000) DEFAULT (''),
    Race VARCHAR(1000) DEFAULT (''),
    Disability VARCHAR(1000) DEFAULT (''),
    [Language] VARCHAR(1000) DEFAULT (''),
    TribalAffiliation VARCHAR(1000) DEFAULT (''),
    NumberDisciplineIncidents INT NOT NULL DEFAULT (0),
    AverageGrade DECIMAL(6,3),
    AttendanceRate DECIMAL(6,3),
    AssessmentScore DECIMAL(6,3)
);


with race as (
    select
        StudentLocalEducationAgencyKey,
        demographics.DemographicLabel
    from
        analytics.StudentLocalEducationAgencyDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'Race'
), disability as (
    select
        StudentLocalEducationAgencyKey,
        demographics.DemographicLabel
    from
        analytics.StudentLocalEducationAgencyDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'Disability'
), [language] as (
    select
        StudentLocalEducationAgencyKey,
        demographics.DemographicLabel
    from
        analytics.StudentLocalEducationAgencyDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'Language'
), tribalAffiliation as (
    select
        StudentLocalEducationAgencyKey,
        demographics.DemographicLabel
    from
        analytics.StudentLocalEducationAgencyDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'TribalAffiliation'
)
insert into edfi_dei.leaStudents (
    LocalEducationAgencyKey,
    StudentLocalEducationAgencyKey,
    StudentKey,
    LimitedEnglishProficiency,
    IsHispanic,
    Sex,
    Race,
    Disability,
    [Language],
    TribalAffiliation
)
select
    student.LocalEducationAgencyKey,
    student.StudentLocalEducationAgencyKey,
    student.StudentKey,
    CASE WHEN student.LimitedEnglishProficiency = 'Not Applicable' THEN 'No'
         ELSE 'Yes' END,
    CASE WHEN student.IsHispanic = 1 THEN 'Yes' ELSE 'No' END,
    student.Sex,
    race.DemographicLabel as Race,
    disability.DemographicLabel as Disability,
    [language].DemographicLabel as [Language],
    tribalAffiliation.DemographicLabel as TribalAffiliation
from
    analytics.StudentLocalEducationAgencyDim student
left outer join
    race
on
    student.StudentLocalEducationAgencyKey = race.StudentLocalEducationAgencyKey
left outer join
    disability
on
    student.StudentLocalEducationAgencyKey = disability.StudentLocalEducationAgencyKey
left outer join
    [language]
on
    student.StudentLocalEducationAgencyKey = [language].StudentLocalEducationAgencyKey
left outer join
    tribalAffiliation
on
    student.StudentLocalEducationAgencyKey = tribalAffiliation.StudentLocalEducationAgencyKey;


---Let's look at average number of discipline incidents for a student across
-- all schools in the district.
--
with incidenceCounts as (
    select
        students.StudentLocalEducationAgencyKey,
        SUM(CASE WHEN discipline.StudentKey IS NOT NULL THEN 1 ELSE 0 END) as NumberOfIncidents
    from
        edfi_dei.leaStudents students
    inner join
        analytics.SchoolDim school
    on
        students.LocalEducationAgencyKey = school.LocalEducationAgencyKey
    left outer join
        analytics.equity_StudentDisciplineActionDim discipline
    on
        students.StudentKey = discipline.StudentKey
    and
        school.SchoolKey = discipline.SchoolKey
    group by
        students.StudentLocalEducationAgencyKey
)
update
    edfi_dei.leaStudents
set
    NumberDisciplineIncidents = ic.NumberOfIncidents
from
    edfi_dei.leaStudents
inner join
    incidenceCounts ic
on
    edfi_dei.leaStudents.StudentLocalEducationAgencyKey = ic.StudentLocalEducationAgencyKey;



-- Average grade for a student across all schools in the district.
--
with grades as (
    select
        students.StudentLocalEducationAgencyKey,
        AVG(grade.NumericGradeEarned) as AvgNumericGradeEarned
    from
        edfi_dei.leaStudents students
    inner join
        analytics.SchoolDim school
    on
        students.LocalEducationAgencyKey = school.LocalEducationAgencyKey
    left outer join
        analytics.ews_StudentSectionGradeFact grade
    on
        students.StudentKey = grade.StudentKey
    and
        school.SchoolKey = grade.SchoolKey
    group by
        students.StudentLocalEducationAgencyKey
)
update
    edfi_dei.leaStudents
set
    AverageGrade = ic.AvgNumericGradeEarned
from
    edfi_dei.leaStudents
inner join
    grades ic
on
    edfi_dei.leaStudents.StudentLocalEducationAgencyKey = ic.StudentLocalEducationAgencyKey;


-- Attendance rate
--
with attendance as (
    select
        students.StudentLocalEducationAgencyKey,
        SUM(CASE WHEN attendance.ReportedAsAbsentFromAnySection + attendance.ReportedAsAbsentFromHomeRoom + attendance.ReportedAsAbsentFromSchool > 0 THEN 1.0 ELSE 0.0 END) as DaysAbsent,
        COUNT(1.0) as EnrolledDays
    from
        edfi_dei.leaStudents students
    inner join
        analytics.SchoolDim school
    on
        students.LocalEducationAgencyKey = school.LocalEducationAgencyKey
    left outer join
        analytics.chrab_ChronicAbsenteeismAttendanceFact attendance
    on
        students.StudentKey = attendance.StudentKey
    and
        school.SchoolKey = attendance.SchoolKey
    group by
        students.StudentLocalEducationAgencyKey
)
update
    edfi_dei.leaStudents
set
    AttendanceRate = (EnrolledDays - DaysAbsent)/EnrolledDays
from
    edfi_dei.leaStudents
inner join
    attendance ic
on
    edfi_dei.leaStudents.StudentLocalEducationAgencyKey = ic.StudentLocalEducationAgencyKey

;

--
---- What about assessments?
--
-- look at individual objectives
with assessments as (
    select
        Student.StudentUniqueId as StudentKey,
        StudentAssessmentStudentObjectiveAssessmentScoreResult.Result,
        ObjectiveAssessment.MaxRawScore,
        case when
                        try_cast(StudentAssessmentStudentObjectiveAssessmentScoreResult.Result as decimal) is null
                    then null
                    else cast(StudentAssessmentStudentObjectiveAssessmentScoreResult.Result as decimal) / ObjectiveAssessment.MaxRawScore
        end as PercentScore
    from
        edfi.StudentAssessmentStudentObjectiveAssessment

    inner join
        edfi.StudentAssessmentStudentObjectiveAssessmentScoreResult
    on
        StudentAssessmentStudentObjectiveAssessment.AssessmentIdentifier = StudentAssessmentStudentObjectiveAssessmentScoreResult.AssessmentIdentifier
    and
        StudentAssessmentStudentObjectiveAssessment.IdentificationCode = StudentAssessmentStudentObjectiveAssessmentScoreResult.IdentificationCode
    and
        StudentAssessmentStudentObjectiveAssessment.Namespace = StudentAssessmentStudentObjectiveAssessmentScoreResult.Namespace
    and
        StudentAssessmentStudentObjectiveAssessment.StudentAssessmentIdentifier = StudentAssessmentStudentObjectiveAssessmentScoreResult.StudentAssessmentIdentifier
    and
        StudentAssessmentStudentObjectiveAssessment.StudentUSI = StudentAssessmentStudentObjectiveAssessmentScoreResult.StudentUSI

    inner join
        edfi.StudentAssessment
    on
        StudentAssessment.AssessmentIdentifier = StudentAssessmentStudentObjectiveAssessment.AssessmentIdentifier
    AND
        StudentAssessment.Namespace = StudentAssessmentStudentObjectiveAssessment.Namespace
    AND
        StudentAssessment.StudentAssessmentIdentifier = StudentAssessmentStudentObjectiveAssessment.StudentAssessmentIdentifier
    AND
        StudentAssessment.StudentUSI = StudentAssessmentStudentObjectiveAssessment.StudentUSI

    inner join
        edfi.ObjectiveAssessment
    on
        StudentAssessmentStudentObjectiveAssessment.AssessmentIdentifier = ObjectiveAssessment.AssessmentIdentifier
    and
        StudentAssessmentStudentObjectiveAssessment.Namespace = ObjectiveAssessment.Namespace
    and
        StudentAssessmentStudentObjectiveAssessment.IdentificationCode = ObjectiveAssessment.IdentificationCode

    inner join
        edfi.Student
    on
        StudentAssessment.StudentUSI = Student.StudentUSI
), students as (
    select
        students.StudentLocalEducationAgencyKey,
        AVG(PercentScore) as AvgPercentScore
    from
        assessments
    inner join
        edfi_dei.leaStudents students
    on
        assessments.StudentKey = students.StudentKey
    group by
        students.StudentLocalEducationAgencyKey
)
update
    edfi_dei.leaStudents
set
    AssessmentScore = AvgPercentScore
from
    edfi_dei.leaStudents
inner join
    students ic
on
    edfi_dei.leaStudents.StudentLocalEducationAgencyKey = ic.StudentLocalEducationAgencyKey

;


--
---- Now look at demographics defined on the school relationship
--

-- Start over...
-- DROP TABLE edfi_dei.schoolStudents

create table edfi_dei.schoolStudents (
    SchoolKey VARCHAR(1000),
    StudentSchoolKey VARCHAR(1000),
    StudentKey VARCHAR(1000),
    LimitedEnglishProficiency VARCHAR(3) DEFAULT (''),
    IsHispanic VARCHAR(3) DEFAULT (''),
    Sex VARCHAR(1000) DEFAULT (''),
    Race VARCHAR(1000) DEFAULT (''),
    Disability VARCHAR(1000) DEFAULT (''),
    [Language] VARCHAR(1000) DEFAULT (''),
    TribalAffiliation VARCHAR(1000) DEFAULT (''),
    NumberDisciplineIncidents INT NOT NULL DEFAULT (0),
    AverageGrade DECIMAL(6,3),
    AttendanceRate DECIMAL(6,3),
    AssessmentScore DECIMAL(6,3)
);

with race as (
    select
        StudentSchoolKey,
        demographics.DemographicLabel
    from
        analytics.StudentSchoolDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'Race'
), disability as (
    select
        StudentSchoolKey,
        demographics.DemographicLabel
    from
        analytics.StudentSchoolDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'Disability'
), [language] as (
    select
        StudentSchoolKey,
        demographics.DemographicLabel
    from
        analytics.StudentSchoolDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'Language'
), tribalAffiliation as (
    select
        StudentSchoolKey,
        demographics.DemographicLabel
    from
        analytics.StudentSchoolDemographicsBridge bridge
    inner join
        analytics.DemographicDim demographics
    on
        bridge.DemographicKey = demographics.DemographicKey
    where
        demographics.DemographicParentKey = 'TribalAffiliation'
)
insert into edfi_dei.schoolStudents (
    SchoolKey,
    StudentSchoolKey,
    StudentKey,
    LimitedEnglishProficiency,
    IsHispanic,
    Sex,
    Race,
    Disability,
    [Language],
    TribalAffiliation
)
select
    student.SchoolKey,
    student.StudentSchoolKey,
    student.StudentKey,
    CASE WHEN student.LimitedEnglishProficiency = 'Not Applicable' THEN 'No'
         ELSE 'Yes' END,
    CASE WHEN student.IsHispanic = 1 THEN 'Yes' ELSE 'No' END,
    student.Sex,
    race.DemographicLabel as Race,
    disability.DemographicLabel as Disability,
    [language].DemographicLabel as [Language],
    tribalAffiliation.DemographicLabel as TribalAffiliation
from
    analytics.StudentSchoolDim student
left outer join
    race
on
    student.StudentSchoolKey = race.StudentSchoolKey
left outer join
    disability
on
    student.StudentSchoolKey = disability.StudentSchoolKey
left outer join
    [language]
on
    student.StudentSchoolKey = [language].StudentSchoolKey
left outer join
    tribalAffiliation
on
    student.StudentSchoolKey = tribalAffiliation.StudentSchoolKey;


---Let's look at average number of discipline incidents for a student across
-- all schools in the district.
--
with incidenceCounts as (
    select
        students.StudentSchoolKey,
        SUM(CASE WHEN discipline.StudentKey IS NOT NULL THEN 1 ELSE 0 END) as NumberOfIncidents
    from
        edfi_dei.schoolStudents students
    inner join
        analytics.equity_StudentDisciplineActionDim discipline
    on
        students.StudentSchoolKey = discipline.StudentSchoolKey
    group by
        students.StudentSchoolKey
)
update
    edfi_dei.schoolStudents
set
    NumberDisciplineIncidents = ic.NumberOfIncidents
from
    edfi_dei.schoolStudents
inner join
    incidenceCounts ic
on
    edfi_dei.schoolStudents.StudentSchoolKey = ic.StudentSchoolKey;



-- Average grade for a student across all schools in the district.
--
with grades as (
    select
        students.StudentSchoolKey,
        AVG(grade.NumericGradeEarned) as AvgNumericGradeEarned
    from
        edfi_dei.schoolStudents students
    inner join
        analytics.ews_StudentSectionGradeFact grade
    on
        students.StudentKey = grade.StudentKey
    and
        students.SchoolKey = grade.SchoolKey
    group by
        students.StudentSchoolKey
)
update
    edfi_dei.schoolStudents
set
    AverageGrade = ic.AvgNumericGradeEarned
from
    edfi_dei.schoolStudents
inner join
    grades ic
on
    edfi_dei.schoolStudents.StudentSchoolKey = ic.StudentSchoolKey;


-- Attendance rate
--
with attendance as (
    select
        students.StudentSchoolKey,
        SUM(CASE WHEN attendance.ReportedAsAbsentFromAnySection + attendance.ReportedAsAbsentFromHomeRoom + attendance.ReportedAsAbsentFromSchool > 0 THEN 1.0 ELSE 0.0 END) as DaysAbsent,
        COUNT(1.0) as EnrolledDays
    from
        edfi_dei.schoolStudents students
    inner join
        analytics.chrab_ChronicAbsenteeismAttendanceFact attendance
    on
        students.StudentSchoolKey = attendance.StudentSchoolKey
    group by
        students.StudentSchoolKey
)
update
    edfi_dei.schoolStudents
set
    AttendanceRate = (EnrolledDays - DaysAbsent)/EnrolledDays
from
    edfi_dei.schoolStudents
inner join
    attendance ic
on
    edfi_dei.schoolStudents.StudentSchoolKey = ic.studentSchoolKey

;

--
---- What about assessments?
--
-- look at individual objectives
with assessments as (
    select
        Student.StudentUniqueId as StudentKey,
        StudentAssessmentStudentObjectiveAssessmentScoreResult.Result,
        ObjectiveAssessment.MaxRawScore,
        case when
                        try_cast(StudentAssessmentStudentObjectiveAssessmentScoreResult.Result as decimal) is null
                    then null
                    else cast(StudentAssessmentStudentObjectiveAssessmentScoreResult.Result as decimal) / ObjectiveAssessment.MaxRawScore
        end as PercentScore
    from
        edfi.StudentAssessmentStudentObjectiveAssessment

    inner join
        edfi.StudentAssessmentStudentObjectiveAssessmentScoreResult
    on
        StudentAssessmentStudentObjectiveAssessment.AssessmentIdentifier = StudentAssessmentStudentObjectiveAssessmentScoreResult.AssessmentIdentifier
    and
        StudentAssessmentStudentObjectiveAssessment.IdentificationCode = StudentAssessmentStudentObjectiveAssessmentScoreResult.IdentificationCode
    and
        StudentAssessmentStudentObjectiveAssessment.Namespace = StudentAssessmentStudentObjectiveAssessmentScoreResult.Namespace
    and
        StudentAssessmentStudentObjectiveAssessment.StudentAssessmentIdentifier = StudentAssessmentStudentObjectiveAssessmentScoreResult.StudentAssessmentIdentifier
    and
        StudentAssessmentStudentObjectiveAssessment.StudentUSI = StudentAssessmentStudentObjectiveAssessmentScoreResult.StudentUSI

    inner join
        edfi.StudentAssessment
    on
        StudentAssessment.AssessmentIdentifier = StudentAssessmentStudentObjectiveAssessment.AssessmentIdentifier
    AND
        StudentAssessment.Namespace = StudentAssessmentStudentObjectiveAssessment.Namespace
    AND
        StudentAssessment.StudentAssessmentIdentifier = StudentAssessmentStudentObjectiveAssessment.StudentAssessmentIdentifier
    AND
        StudentAssessment.StudentUSI = StudentAssessmentStudentObjectiveAssessment.StudentUSI

    inner join
        edfi.ObjectiveAssessment
    on
        StudentAssessmentStudentObjectiveAssessment.AssessmentIdentifier = ObjectiveAssessment.AssessmentIdentifier
    and
        StudentAssessmentStudentObjectiveAssessment.Namespace = ObjectiveAssessment.Namespace
    and
        StudentAssessmentStudentObjectiveAssessment.IdentificationCode = ObjectiveAssessment.IdentificationCode

    inner join
        edfi.Student
    on
        StudentAssessment.StudentUSI = Student.StudentUSI
), students as (
    select
        students.StudentSchoolKey,
        AVG(PercentScore) as AvgPercentScore
    from
        assessments
    inner join
        edfi_dei.schoolStudents students
    on
        assessments.StudentKey = students.StudentKey
    group by
        students.StudentSchoolKey
)
update
    edfi_dei.schoolStudents
set
    AssessmentScore = AvgPercentScore
from
    edfi_dei.schoolStudents
inner join
    students ic
on
    edfi_dei.schoolStudents.StudentSchoolKey = ic.studentSchoolKey

;
