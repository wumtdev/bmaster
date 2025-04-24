
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from bmaster import icoms, logs
from bmaster.icoms.queries import QueryAuthor, SoundQuery
from bmaster.scheduling import scheduler
from datetime import time, datetime
from bmaster.api import api

from bmaster.utils import TimeHHMM


logger = logs.logger.getChild('lite')
router = APIRouter(tags=['lite'])


SETTINGS_PATH = Path('data/lite.json')
WEEKDAY_MAP = {
	0: 'monday',
	1: 'tuesday',
	2: 'wednesday',
	3: 'thursday',
	4: 'friday',
	5: 'saturday',
	6: 'sunday'
}
ICOM_ID = 'main'

class Lesson(BaseModel):
	enabled: bool
	start_at: TimeHHMM
	start_sound: Optional[str] = None
	end_at: TimeHHMM
	end_sound: Optional[str] = None

class LessonWeekdays(BaseModel):
	monday: bool
	tuesday: bool
	wednesday: bool
	thursday: bool
	friday: bool
	saturday: bool
	sunday: bool

	def get_by_number(self, num: int) -> bool:
		return getattr(self, WEEKDAY_MAP[num])

class BellsSettings(BaseModel):
	lessons: list[Lesson]
	enabled: bool
	weekdays: LessonWeekdays

class AnnouncementsSettings(BaseModel):
	ring_sound: Optional[str] = None

class LiteSettings(BaseModel):
	bells: BellsSettings
	announcements: AnnouncementsSettings

	@staticmethod
	def default():
		return LiteSettings(
			bells=BellsSettings(
				lessons=[],
				enabled=True,
				weekdays=LessonWeekdays(
					monday=True,
					tuesday=True,
					wednesday=True,
					thursday=True,
					friday=True,
					saturday=False,
					sunday=False
				)
			),
			announcements=AnnouncementsSettings(
				ring_sound=None
			)
		)




settings: Optional[LiteSettings] = None

async def load_settings():
	global settings
	if SETTINGS_PATH.exists():
		try:
			data = SETTINGS_PATH.read_text(encoding='utf8')
			settings = LiteSettings.model_validate_json(data)
		except Exception as e:
			logger.error(f"Failed to load settings: {e}")
			raise
			# settings = LiteSettings(lessons_list=[], lessons_enabled=False, lessons_weekdays=LessonWeekdays(
			# 	monday=False, tuesday=False, wednesday=False, thursday=False, friday=False, saturday=False, sunday=False))
	else:
		settings = LiteSettings.default()
		await save_settings()

async def save_settings():
	if settings:
		try:
			SETTINGS_PATH.write_text(settings.model_dump_json(indent=4), encoding='utf8')
		except Exception as e:
			logger.error(f"Failed to save settings: {e}")


async def on_lesson_start(lesson_id: int):
	bells = settings.bells
	try:
		lesson = bells.lessons[lesson_id]
	except IndexError:
		logger.error(f'Orphan job of start lesson #{lesson_id} detected')
		return
	
	if not (bells.enabled and lesson.enabled and lesson.start_sound): return
	now = datetime.now()
	if not bells.weekdays.get_by_number(now.weekday()): return

	# Play sound
	SoundQuery(
		icom=icoms.get(ICOM_ID),
		sound_name=lesson.start_sound,
		priority=0,
		force=False,
		author=QueryAuthor(
			type='service',
			name='Расписание'
		)
	)

async def on_lesson_end(lesson_id: int):
	bells = settings.bells
	try:
		lesson = bells.lessons[lesson_id]
	except IndexError:
		logger.error(f'Orphan job of end lesson #{lesson_id} detected')
		return
	
	if not (bells.enabled and lesson.enabled and lesson.end_sound): return
	now = datetime.now()
	if not bells.weekdays.get_by_number(now.weekday()): return

	# Play sound
	SoundQuery(
		icom=icoms.get(ICOM_ID),
		sound_name=lesson.end_sound,
		priority=0,
		force=False,
		author=QueryAuthor(
			type='service',
			name='Расписание'
		)
	)

async def reschedule_lessons():
	# Clear old schedule jobs
	for job in scheduler.get_jobs(jobstore='temp'):
		if job.id.startswith('lite.lesson'):
			job.remove()
	
	lessons = settings.bells.lessons
	for i, lesson in enumerate(lessons):
		scheduler.add_job(
			jobstore='temp',
			id=f'lite.lesson.start#{i}',
			func=on_lesson_start,
			trigger='cron',
			hour=lesson.start_at.hour,
			minute=lesson.start_at.minute,
			kwargs={
				'lesson_id': i
			}
		)
		scheduler.add_job(
			jobstore='temp',
			id=f'lite.lesson.end#{i}',
			func=on_lesson_end,
			trigger='cron',
			hour=lesson.end_at.hour,
			minute=lesson.end_at.minute,
			kwargs={
				'lesson_id': i
			}
		)


async def start():
	await load_settings()
	await reschedule_lessons()
	api.include_router(router, prefix='/lite')


@api.get('/lite/bells', tags=['lite'])
async def get_bells_settings() -> BellsSettings:
	return settings.bells


class BellsPatchRequest(BaseModel):
	lessons: Optional[list[Lesson]] = None
	enabled: Optional[bool] = None
	weekdays: Optional[LessonWeekdays] = None

@api.patch('/lite/bells', tags=['lite'])
async def patch_bells_settings(req: BellsPatchRequest):
	bells = settings.bells
	if req.lessons is not None:
		bells.lessons = req.lessons
	if req.enabled is not None:
		bells.enabled = req.enabled
	if req.weekdays is not None:
		bells.weekdays = req.weekdays
	await save_settings()
	if req.lessons is not None:
		await reschedule_lessons()

class LessonPatchRequest(BaseModel):
	enabled: Optional[bool] = None

@api.patch('/lite/bells/lessons/{lesson_id}', tags=['lite'])
async def patch_lesson(lesson_id: int, req: LessonPatchRequest):
	global settings
	try:
		lesson = settings.bells.lessons[lesson_id]
	except IndexError:
		raise HTTPException(status.HTTP_404_NOT_FOUND, 'Lesson not found')
	
	if req.enabled is not None:
		lesson.enabled = req.enabled
	await save_settings()


@api.get('/lite/announcements', tags=['lite'])
async def get_announcements_settings() -> AnnouncementsSettings:
	return settings.announcements

class AnnouncementsSettingsPatchRequest(BaseModel):
	ring_sound: Optional[str] = None

@api.patch('/lite/announcements', tags=['lite'])
async def patch_announcements_settings(req: AnnouncementsSettingsPatchRequest):
	settings.announcements.ring_sound = req.ring_sound
	await save_settings()
